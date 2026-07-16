# The Trail Language Reference

**Version:** 0.3-draft · 2026-07-15
**Status:** Normative for phase 1 (language core); phase 2+ constructs are marked with *(phase N)*. The data model is `(entity x time@frequency)`; cross-frequency alignment (§4.4) is specified here and lands in the reference implementation in phases.

This document is the authoritative specification of the Trail language: its lexical structure, data model, expression semantics, built-in functions, declarations, diagnostics, and runtime configuration.

---

## 1. Introduction

Trail is a small, total, declarative language for computing financial indicators, scores, and screening strategies over panels of entities. Trail programs are written by humans and by AI agents; they are data - stored, diffed, validated, generated - not code.

A representative program:

```trail
universe us_main = stocks where meta.exchange in ("NYSE", "NASDAQ") and meta.is_active

model quality on us_main at annual {
    desc "Margin quality with trend confirmation"

    operating_margin = income.operating_income / income.revenue

    score om_score weight 7 {
        2 if operating_margin > 0.12
        1 if operating_margin > 0.05
        else 0
    }

    export composite = weighted_score()
}
```

### 1.1 Design invariants

Every conforming implementation MUST preserve:

- **I1 - Panel model.** Every field and every expression denotes a value per `(entity, time)` cell. There is no scalar context and no per-entity iteration; the two axes are fixed.
- **I2 - Totality.** Every Trail program terminates. The language has no loops and no recursion. User-defined functions (`def`, §8.8) are permitted but are **non-recursive expression macros** - inlined at their call sites before compilation - so they add no computational power that could threaten termination or static analysis.
- **I3 - Static analyzability.** A program's complete data requirements - fields, sources, window lengths, functions - are derivable without executing it.
- **I4 - Point-in-time safety.** No expression can observe data from a later period than the cell it computes. Forward-looking constructs are legal only inside `learn.target`.
- **I5 - Vectorized execution.** Every construct lowers to columnar operations; implementations MUST NOT execute per-row interpreted code for any built-in.

These invariants are what make Trail safe for agent authorship: a program that parses and validates is guaranteed to terminate, to have known data needs, and to be incapable of look-ahead bias.

### 1.2 Conformance phases

| Phase | Constructs |
|---|---|
| 1 (normative here) | expressions, built-ins (§7 except items marked deferred), user-defined functions (`def`, §8.8), `universe`, `model`, `score`, `signal`, runtime config (§10), the interactive dialect and discovery meta-commands (§1.3); `strategy`/`backtest`/`learn`/`import` parse without execution |
| 2 | `import` inclusion, source pinning `@`, multi-source resolution, cross-model export references, `quarterly`/`monthly` contexts, `sply`, `ttm`, `roll_tail_mean`, `on_missing median`, registered functions |
| 3 | `strategy`/`backtest` execution (gates, fallback sleeves, exposure) |
| 4 | `learn` execution, weight tables |

A phase-1 implementation MUST reject constructs it cannot execute using the diagnostics of §9 - never by silently ignoring them.

### 1.3 Two dialects: model files and the interactive REPL

Trail has two parse surfaces that share one lexer and one expression grammar but differ at the top level:

- **The file grammar** (`start`, §12) - the language proper. A `.trail` file is a sequence of declarations (§8): pure panel computation, total, statically analyzable, side-effect-free. This is what agents generate, what `deps.extract` plans against, and what gets version-controlled. It contains **no** meta-commands.
- **The interactive dialect** (`repl_line`, §12) - a strict superset for REPLs, notebooks, and other interactive front-ends. A repl line is a **meta-command**, a declaration, or a bare expression. It exists so interactive discovery and evaluation feel native without polluting the file format.

This split is deliberate: discovery is an authoring-time question ("what *can* I write?"), not a computation ("what does this compute?"). Keeping meta-commands in the interactive dialect only means a model file stays a clean computation artifact - a meta-command in a file is a syntax error (mirroring how IPython magics are invalid in a `.py` module).

**Meta-commands** begin with `?` and return a **catalog result** - a titled metadata table (fields, functions, sources), never a `(entity × time)` panel. They are a distinct value domain from expressions; an implementation MUST NOT let a meta-command flow into panel computation.

| Form | Meaning |
|---|---|
| `?` | the full catalog: namespaces and their field counts, plus function/source totals |
| `?<namespace>` | list the fields (and kinds) in a namespace - e.g. `?income` |
| `?<namespace>.<field>` | describe one field (column, kind) - e.g. `?income.revenue` |
| `?<function>` | describe a built-in (axis, arity, summary) - e.g. `?cagr` |
| `?<source>` | describe a configured source (driver, options) - e.g. `?fmp` |
| `?fields` \| `?functions` \| `?sources` | list all fields / all functions / all configured sources |

The resolver disambiguates a single `?<name>` by lookup order: exact field path → namespace → function → source → the `fields`/`functions`/`sources` category words → "unknown".

**Discovery front-ends.** The catalog engine is a single core; meta-commands are one front-end onto it. The same core backs the `trail catalog [target]` CLI command (phase 1), and - as they land - an MCP discovery tool and Jupyter line/cell magics (`%trail`, `%%trail`). Field availability is reported from the schema in phase 1; once real source drivers exist (phase 2) discovery additionally reports **per-source** resolution, which doubles as the source coverage probe.

Discovery reads only the registries (schema, built-in functions, configured sources) and never executes a program, so it is always safe and side-effect-free.

---

## 2. Notation and terminology

Grammar excerpts use Lark notation: `"literal"` terminals, `UPPER` token names, `lower` rules, `?rule` inlined-when-single-child, `x*`/`x+`/`x?` repetition. The complete normative grammar is §12.

- **Panel** - a rectangular association from `(entity, time)` to values; the sole evaluation domain.
- **Cell** - one `(entity, time)` position.
- **Broadcast series** - a panel whose value is constant across the entity axis (index levels, macro rates, universe aggregates).
- **Group** - the set of cells a cross-sectional operator computes within: `(time × universe)`, optionally refined by a `by` field.
- **PIT date** - the first calendar date at which a cell's value was knowable (filing date plus configured lag).

---

## 3. Lexical structure

**Encoding** is UTF-8. **Whitespace** separates tokens and is otherwise insignificant; statements are newline-separated by convention but delimited by the grammar, not by newlines.

**Comments** run from `#` to end of line and may appear anywhere whitespace may:

```trail
# a full-line comment
roa = income.net_income / avg2(balance.total_assets)   # trailing comment
```

Comments are not tokens; implementations MAY preserve them for formatting tools.

### 3.1 Tokens

| Token | Pattern | Valid examples | Invalid examples |
|---|---|---|---|
| NUMBER | `/[0-9][0-9_]*(\.[0-9]+)?([eE][+-]?[0-9]+)?/` | `0`, `2.5`, `200e6`, `1_000_000`, `4.5e-2` | `-3` (unary minus is an operator), `.5` (leading digit required), `1.` (trailing digit required) |
| STRING | `/"[^"]*"/` | `"NYSE"`, `"Total Debt"` | `'NYSE'` (single quotes), escapes (none in v0.2) |
| Boolean | `true` \| `false` | `true` | `True`, `TRUE` |
| NAME | `/[a-zA-Z_][a-zA-Z0-9_]*/`, excluding reserved words | `roa`, `fcf_per_share`, `_tmp` | `3yr_avg` (leading digit), `weight` (reserved) |
| DATE | `/\d{4}-\d{2}(-\d{2})?/` | `2010-01`, `2025-12-31` | `2010/01` |
| DURATION | `/\d+[dmy]/` | `45d`, `3m`, `1y` | `45 days` |

**Operators and punctuation:** `+ - * / % ^ == != > < >= <= ?? @ = . , ( ) { } ..`

### 3.2 Reserved words

The following cannot be used as assignment, score, model, universe, signal, or strategy names:

```
and annual at backtest by cash costs daily def else equal export exposure
fallback false for from gate hold_band hourly if import in learn median minute
model monthly not on on_missing or pit_lag quarterly rebalance report score
select signal skip strategy tbills to top true universe validate value weekly
weight weighting weights where zero
```

Reserved words ARE permitted as trailing components of a dotted field path (`meta.value` is legal; `value = …` is not).

---

## 4. Data model

### 4.1 Panels

The evaluation domain is the **panel**: rows keyed by `(entity, time)`. An **entity** is any subject a data provider reports on - a stock, a country, a currency pair, a commodity, an index (an opaque canonical identifier; see §5.4). **`time`** is a point on a real temporal axis at a declared **frequency** (§4.4), canonicalized to the period-end instant. Writing a field name denotes the entire panel:

`income.revenue` over a 3-entity universe, annual frequency:

| entity \ time | 2021-12-31 | 2022-12-31 | 2023-12-31 | 2024-12-31 |
|---|---|---|---|---|
| AAA | 100 | 110 | 121 | 133.1 |
| BBB | 200 | 210 | 220 | 231 |
| CCC | 300 | 270 | 300 | 330 |

All arithmetic is cell-aligned on `(entity, time)` - never positional. `income.net_income / income.revenue` divides each cell by the matching cell. A scalar literal broadcasts to every cell: `income.revenue * 2` doubles the grid. Fields native to different frequencies are aligned to a common `time` grid before they meet (§4.4).

Broadcast series occupy the same domain with a constant entity axis. `macro.risk_free` at 2024 has one value repeated for every entity; `earnings_yield > macro.risk_free + 0.02` therefore compares each entity's cell against the same hurdle - this is how "floating thresholds" work with no special construct.

### 4.2 Fields, namespaces, kinds

Schema fields are addressed by dotted path. Standard namespaces:

| Namespace | Content | Examples |
|---|---|---|
| `income.*` | income-statement items | `revenue`, `operating_income`, `eps_diluted`, `interest_expense` |
| `balance.*` | balance-sheet items | `total_assets`, `total_debt`, `retained_earnings`, `inventory` |
| `cash.*` | cash-flow items | `cfo`, `capex`, `free_cash_flow`, `stock_issued` |
| `price.*` | market data, PIT-aligned (§4.4) | `adj_close`, `dividends`, `return`, `volume` |
| `meta.*` | classification and listing data | `sector`, `exchange`, `market_cap`, `is_active`, `country` |
| `index.*` | index-level broadcast series | `spx.close`, `spx.return`, `spx.eps` |
| `macro.*` | macro broadcast series | `risk_free`, `treasury_10y`, `cpi` |
| `estimates.*` | analyst estimates (PIT-legal, §4.5) | `eps_fwd`, `eps_growth_fwd`, `revision_score` |
| `insider.*`, `ownership.*`, `sentiment.*`, `attention.*` | event-derived panels, pre-aggregated by the data layer | `insider.net_buy_value_6m`, `ownership.short_interest_pct` |

Every field carries a **kind** that identifies its measure and - crucially - **how it aggregates when its frequency changes** (§4.4). Built-in kinds and their default downsample rule: `flow` (income/cash items, summable across periods -> **sum**), `stock`/`level`/`price` (point-in-time snapshots -> **last**), `rate`/`ratio` (-> **mean**), `index` (CPI, REER -> **last**), `return` (period returns -> **compound**), `per_share` (-> **sum**), `meta` (categorical -> **last**), plus `days`, `count`. Kinds also drive `ttm`/`avg2` behavior and lint diagnostics; kind violations are warnings, not errors - the canonical example:

```trail
inventory_turnover = income.cogs / balance.inventory          # W-KIND-STOCK-FLOW
inventory_turnover = income.cogs / avg2(balance.inventory)    # clean: flow over averaged stock
```

The vocabulary is **extensible**: a data-source package contributes its own namespace and kinds (e.g. `gmd.*` macro fields) through the `trail.schema` mechanism (§10.2). Contributed fields validate, appear in the catalog, and resample by kind exactly like built-ins; kinds are freeform strings, and only `flow`/`stock` carry the stock-flow lint.

### 4.3 Null semantics

Missing data is **null** (not NaN). Null is an ordinary value that flows through computation; nothing in the language raises a runtime error. Normative rules, each with its consequence:

1. **Arithmetic and comparison propagate null.** `null + 5 → null`; `null > 0.12 → null` (not `false`). A boolean flag can therefore be null.
2. **Division by zero is null**, never ±∞: `x / 0 → null`, `x % 0 → null`.
3. **Domain violations are null**: `sqrt(-4) → null`, `log(0) → null`, `(-8) ^ 0.5 → null`.
4. **Null conditions do not match.** In score blocks and ternaries, a null condition falls through to the next case / `else`:
   ```trail
   # x present but ≤ 0.12  →  condition false  →  falls through  →  result 0
   score s weight 1 { 2 if x > 0.12; else 0 }
   ```
   Note the asymmetry with rule 1: a *bare* comparison stored in a flag stays null; only *match positions* treat null as non-matching.
   **Exception - the all-null case:** a score whose *every* case condition is null (all its inputs are missing) is itself **null**, not the `else` value. This is what makes `on_missing skip` meaningful - a metric a company simply cannot compute (e.g. a bank with no inventory) drops out and renormalizes, rather than silently scoring `else`. If at least one condition is evaluable (true or false), normal first-match-wins applies.
5. **Coalesce:** `x ?? y` yields `x` where `x` is non-null, else `y`. Left-associative chains: `a ?? b ?? 0`.
6. **Boolean connectives** follow three-valued logic: `true or null → true`, `false and null → false`, `true and null → null`, `not null → null`. In match positions, rule 4 then governs the residual null.
7. **Windowed operators require full windows.** `roll_*(x, n)` yields null until `n` consecutive periods are available (`min_samples = n`). Partial windows would silently change 3-vs-5-year comparisons, so they are forbidden. Cross-sectional operators (`zscore`, `rank`, …) skip null cells: the group is the non-null members.

Practical consequence for checklists: `count(f1, f2, f3)` propagates null if any flag is null (rule 1). Guard field-dependent flags explicitly:

```trail
f_noissue = (cash.stock_issued ?? 0) == 0    # null issuance data counts as "no issuance"
```

### 4.4 Frequency, contexts, and alignment

Different providers publish at different resolutions - GMD macro series are annual, SEC 10-Q statements quarterly, prices daily or intraday. Every source declares a native **frequency** on the ladder

```
annual < quarterly < monthly < weekly < daily < hourly < minute        (coarse -> fine)
```

A `model`/`signal` computes on one **target frequency**, declared `at <freq>`. When omitted, the target defaults to the **finest** frequency among the fields the block references (least lossy: coarser series are carried onto the finer grid, nothing is aggregated away). The target defines what one step means for every time-series operator in the block: `lag(x, 1)` is one target period, `roll_mean(x, 3)` three target periods.

**Automatic alignment.** Any field whose native frequency differs from the target is aligned before it meets other fields, using its `kind`:

- **coarser than target -> upsample by as-of**: carry the last known value forward (the value in effect at each finer `time`). This is exactly "the annual policy rate that applied on this trading day". Safe for `stock`/`level`/`price`/`rate`/`ratio`/`index`/`meta`. For `flow`/`return`/`per_share` it emits **`W-UPSAMPLE-FLOW`** (repeating a total mis-scales it) and should be handled with an explicit resample.
- **finer than target -> downsample by aggregation**, chosen by kind (§4.2): `flow` -> sum, `stock`/`level`/`index` -> last, `rate`/`ratio` -> mean, `return` -> compound (`prod(1+r)-1`), `meta` -> last.

**Explicit transforms** override the automatic rule:

- `resample(x, freq, agg)` - force a frequency and aggregation.
- `to_annual(x)`, `to_quarterly(x)`, `to_monthly(x)`, `to_daily(x)` - sugar; aggregation by kind unless a second argument overrides.
- `asof(x)` - force as-of (last-known) alignment onto the target grid.
- `ttm(x)` / `trailing(x, "1y")` - trailing-window transform: kind-aware (rolling 4-quarter **sum** for a `flow`, **last** for a `stock`).
- Duration-window rolling: `roll_sum(x, "1y")`, `roll_mean(x, "90d")` - the `roll_*` reducers accept a duration string as the window in addition to an integer count.

The `agg` in `resample`/`to_*` is any reduction from the **aggregation library** (§7.7): `sum`, `mean`, `last`, `first`, `min`, `max`, `count`, `median`, `std`, `var`, `quantile(q)`, `range`, `prod`, `compound`, `geomean`, `change`. Downsampling a target bucket is a reduction over a list of values, so any of these applies; `kind` only supplies the default.

**Worked examples.**

```trail
# daily stock return vs annual country rate: the annual rate (kind=rate) as-of-broadcasts onto each day
model carry at daily {
  export excess = price.return - macro.risk_free
  export ann_vol = resample(price.return, "annual", "std")   # explicit: realized annual volatility
}

# trailing-twelve-months from 10-Q flows (kind-aware)
model ttm at quarterly {
  export revenue_ttm = ttm(income.revenue)      # rolling 4-quarter sum (flow)
  export assets_now  = ttm(balance.total_assets) # last (stock), not summed
}
```

**Point-in-time.** Because `time` is the **period-end** instant and upsampling is a **backward** as-of join, a value is visible only from the moment it is known - alignment is lookahead-safe by construction. Company AAA files FY2023 on 2024-02-15 with `pit_lag 45d`, so its FY2023 cell is knowable as of 2024-03-31; `price.adj_close / income.eps_diluted` at daily target uses each day's close against the most recent *known* EPS, and next year's actual EPS is inexpressible. This alignment is engine-enforced and cannot be written incorrectly.

### 4.5 Point-in-time invariant

- `lag(x, n)` requires a literal `n >= 0`. There is no `lead`.
- `fwd_return(horizon)` is grammatically an ordinary call but is legal only as the `target` of a `learn` declaration; anywhere else it is `E-FWD-CONTEXT`.
- `estimates.*` fields are **not** future references: an analyst's FY-ahead EPS estimate is an opinion knowable at time t, PIT-stamped like any other field. Using `estimates.eps_fwd` in a valuation model is legal; using next year's *actual* EPS is inexpressible.

### 4.6 Universe scoping

Cross-sectional operators and universe aggregates compute within `(time × universe)` - the universe the enclosing `model`/`signal` is bound to via `on`. The same expression yields different values under different universes:

```trail
universe all  = stocks where meta.is_active
universe tech = all where meta.sector == "Tech"

model a on all  at annual { export z = zscore(income.revenue) }  # z vs the whole market
model b on tech at annual { export z = zscore(income.revenue) }  # z vs tech only
```

Universe membership is itself point-in-time: a entity delisted in 2019 is a member for periods before 2019 and absent after. Survivorship-free membership is an engine guarantee, not an author obligation.

---

## 5. Source resolution

*(Execution: phase 2. Phase-1 implementations parse pins and reject them with `E-PIN-UNSUPPORTED`.)*

Trail decouples *what* a field means (the canonical schema) from *where* its values come from (data sources such as FMP, SEC EDGAR, stockanalysis).

### 5.1 Unqualified fields

An unqualified field (`income.revenue`) resolves through the runtime **precedence configuration** (§10): each namespace has an ordered source list; **per cell**, the first source with a non-null value wins.

Example with `precedence: statements: [edgar, fmp]`:

| cell | EDGAR | FMP | `income.revenue` resolves to |
|---|---|---|---|
| (AAA, 2023) | 121.0 | 120.8 | 121.0 (EDGAR first) |
| (AAA, 2024) | null (not yet filed to EDGAR mapping) | 133.1 | 133.1 (falls to FMP) |
| (BBB, 2023) | null | null | null |

### 5.2 Pinned fields

`income.revenue @ fmp` resolves from exactly the source named `fmp` in the configuration; cells that source lacks are null. Pins bind tighter than every binary operator and apply only to schema field references:

```trail
rev_gap = abs(income.revenue @ fmp - income.revenue @ edgar)
        / (income.revenue @ edgar ?? income.revenue @ fmp)      # source-disagreement forensics
```

`(a + b) @ fmp` is a syntax error - pin the fields, not the arithmetic.

### 5.3 Source names

The names after `@` are exactly the keys of the configuration's `sources` map (§10). A pin naming an undeclared source is `E-SOURCE-UNKNOWN`.

### 5.4 Identity and alignment (engine contract)

Panels from different sources align on a **canonical entity identity** (mapped per source from ticker/CIK/ISIN/FIGI) and **canonical fiscal periods**. PIT dates are tracked per `(entity, source)` - the same FY2023 figure may become knowable on different dates from different sources, and PIT alignment (§4.4) uses the resolving source's date. This identity layer is a data-plane obligation; the language never manipulates raw source symbols.

**Broadcast (global) series.** A value with no entity axis - a market-wide risk-free rate, a single macro series - is delivered by a source as a panel keyed by the reserved entity `*`. The engine replicates it across every entity on the target grid by time alignment alone (the value in effect at each instant), so `price.return - macro.risk_free` is well defined for every stock. A broadcast series contributes no rows of its own to the grid, and the language sees an ordinary field; the `*` sentinel is a data-plane convention, not a symbol the author writes.

---

## 6. Expressions

### 6.1 Precedence

Loosest to tightest; parenthesize to override.

| Level | Construct | Associativity | Example parse |
|---|---|---|---|
| 1 | `v if c else e` | right | `2 if a else 1 if b else 0` = `2 if a else (1 if b else 0)` |
| 2 | `or` | left | |
| 3 | `and` | left | `a or b and c` = `a or (b and c)` |
| 4 | `not` | prefix | `not a > 1` = `not (a > 1)` |
| 5 | `== != > < >= <=`, `in (…)` | non-chaining | `a < b < c` is a syntax error |
| 6 | `??` | left | `a ?? b + c` = `a ?? (b + c)` |
| 7 | `+ -` | left | |
| 8 | `* / %` | left | `a + b * c` = `a + (b * c)` |
| 9 | `^` | right | `2 ^ 3 ^ 2` = `2 ^ (3 ^ 2)` = 512 |
| 10 | unary `-` | prefix | `-a ^ 2` = `-(a ^ 2)` … see note |
| 11 | `@ source` | postfix | `x @ fmp ?? y` = `(x @ fmp) ?? y` |
| 12 | call, ref, literal, `( )` | - | |

Note on unary minus and `^`: `-x ^ 2` parses as `-(x ^ 2)` (power binds tighter). Write `(-x) ^ 2` when that is meant.

### 6.2 Operator semantics

- **Arithmetic** `+ - * / % ^` - cell-wise; null per §4.3 rules 1-3. `^` accepts real exponents (`x ^ (1/3)` is a cube root).
- **Comparisons** - produce boolean panels. Comparing a string field to a string literal is legal (`meta.sector == "Tech"`); ordering comparisons on strings are `E-TYPE-ORDER` *(reserved; not checked in phase 1)*.
- **`in`** - membership against a parenthesized literal list: `meta.exchange in ("NYSE", "NASDAQ")`. The list contains literals only, not expressions.
- **`??`** - coalesce (§4.3 rule 5).
- **Ternary** `v if c else e` - cell-wise selection; both branches are (conceptually) evaluated everywhere, which is unobservable since expressions have no effects. Chains right-associate, giving first-match-wins reading order:
  ```trail
  size_bucket = 3 if meta.market_cap > 10e9 else 2 if meta.market_cap > 2e9 else 1
  ```
- **Name references** - a bare NAME resolves to an earlier assignment in the same model (§8.3), never to a field. **Field references** are always dotted. This rule is what makes `roa > lag(roa, 1)` unambiguous.
- **Cross-model references** *(phase 2)* - `quality.composite` (a model name dotted with an export) reads another model's export as a field. The validator resolves model exports before schema namespaces.

---

## 7. Built-in functions

Trail's functionality lives in functions, not operators - the grammar carries only arithmetic, comparison, boolean, ternary, `??`, and call syntax (§6). Functions come in three layers:

- **Primitives** - irreducible operations that introduce the windowing or cross-sectional machinery itself (`lag`, `cummax`, the `roll_*` reducers, the `xs_*` reducers, `rank`, and scalar math like `sqrt`/`log`/`exp`). These cannot be expressed by composition and are implemented directly on the columnar engine. This section catalogs them.
- **Derived functions** - pure compositions of primitives (`yoy = x/lag(x,1)-1`, `avg2`, `beta = roll_cov/roll_var`, most financial ratios, most published factors). These are written **in Trail itself** as a standard library (§8.8), not hand-coded on the engine.
- **Registered functions** - the escape hatch for math that is neither a primitive nor a composition - multivariate regression, matrix/state-space methods (§7.6).

A `def` (§8.8) may compose primitives and other derived functions; it can never define a new primitive. Discovery (§1.3) reports which layer each function belongs to.

Axis legend: **T** = time-series (within each entity, along periods), **X** = cross-sectional (within each period, across the enclosing universe; accepts trailing `by <field>`), **E** = elementwise, **M** = model-context.

Windows, quantiles, and periods (`n`, `q`, `p`) MUST be numeric literals (invariant I3 - static data requirements). `cagr(x, n)` with a computed `n` is `E-ARG-STATIC` *(reserved; enforced structurally in phase 1 by literal-only compilation of these arguments)*.

### 7.1 Time-series functions (T)

All operate within each entity along the time axis and require the panel sorted by time (an engine guarantee).

**`lag(x, n)`** - value `n` periods earlier; the first `n` periods are null.

```
x        : 100  110  121  133.1
lag(x,1) : null 100  110  121
```

**`roll_mean(x, n)`, `roll_sum`, `roll_std`, `roll_var`, `roll_max`, `roll_min`** - rolling window of exactly `n` periods; null until the window is full. `roll_std`/`roll_var` use **sample** statistics (ddof = 1).

```
x            : 10   20   30
roll_mean(x,2): null 15   25
roll_std(x,3) : null null 10        # sample std of {10,20,30}
```

The workbook's dominant idiom composes directly:

```trail
improving = roll_mean(fcf_per_share, 3) > roll_mean(fcf_per_share, 5)
```

**`roll_quantile(x, n, q)`** - rolling `q`-quantile over the window. Historical VaR at 95%: `roll_quantile(price.return, 60, 0.05)`. Quantile interpolation is implementation-defined in v0.2 *(standardization pending)*.

**`roll_tail_mean(x, n, q)`** *(phase 2)* - mean of window values ≤ the `q`-quantile: historical CVaR / expected shortfall.

**`roll_cov(x, y, n)` / `roll_corr(x, y, n)`** - rolling covariance / Pearson correlation of two panels.

**`beta(x, bench, n)`** - `roll_cov(x, bench, n) / roll_var(bench, n)`. With a broadcast benchmark:

```trail
beta_36m   = beta(price.return, index.spx.return, 36)     # monthly context
beta_blume = 0.67 * beta_36m + 0.33
```

**`cummax(x)` / `cumsum(x)` / `cumprod(x)` / `cummin(x)`** - expanding max/sum/product/min from each entity's first period (causal; the building blocks for discrete integrals and compounding).

**`roll_median(x, n)` / `roll_skew(x, n)`** - rolling median and skewness over a trailing window.

**`ewm_mean(x, span)` / `ewm_std(x, span)`** - exponentially-weighted moving mean / std (decay recurrence; the standard EWMA volatility estimator).

**`decay_linear(x, n)`** - linearly-decayed weighted mean over a trailing window (most recent period weighted highest); a common alpha-factor primitive.

**`drawdown(x)`** - `x / cummax(x) - 1`.

```
x           : 10    8     12
cummax(x)   : 10    10    12
drawdown(x) : 0.0  -0.2   0.0
```

Per-entity max drawdown over 5 years (monthly context): `roll_min(drawdown(price.adj_close), 60)`.

> **Now derived (stdlib).** `yoy`, `avg2`, `drawdown`, `cagr`, `increase`, `roll_cov`, `roll_corr`, `beta`, and `pctile` are **not** primitives - they are `def` macros in `stdlib/timeseries.trail` (compositions of `lag`/`roll_*`/`cummax`/`rank`/`xs_count`). They are documented here for reference; the engine no longer implements them. Discovery (§1.3) tags them `derived`.

**`yoy(x)`** - `x / lag(x, 1) - 1`.

**`increase(x, n)`** - `(end' − start') / start'` after the negative-value shift rule (§7.4).

**`cagr(x, n)`** - `(end'/start')^(1/n) − 1` after the shift rule.

```
x (n=3)          : 100 … 133.1     → cagr = (133.1/100)^(1/3) − 1 = 0.10
x (n=3, signed)  : −10 … 60        → start′=10, end′=80 → (80/10)^(1/3) − 1 = 1.00
```

**`avg2(x)`** - `(x + lag(x,1)) / 2`: start/end balance-sheet averaging for turnover and days ratios.

```trail
dso = (avg2(balance.accounts_receivable) / income.revenue) * 365
```

**`sply(x)`**, **`ttm(x)`** *(phase 2)* - see §4.4.

### 7.2 Cross-sectional functions (X)

All compute within the **group**: `(time × universe)`, refined to `(time × universe × field value)` by a trailing `by <field>`. Null cells are excluded from the group.

**`zscore(x)`** - `(x − mean(group)) / std(group)`, sample std (ddof = 1); null if the group std is null or zero.

```
group values {1, 3, 10, 30}: mean 11, std ≈ 13.24
zscore → {−0.76, −0.60, −0.08, +1.44}
```

Sector-neutral form - each entity standardized against its own sector:

```trail
z = zscore(gross_profitability) by meta.sector
```

**`rank(x)`** - ascending, 1-based, average ties: `{5, 5, 7} → {1.5, 1.5, 3}`.

**`pctile(x)`** - `(rank − 1) / (count − 1)` ∈ [0, 1]: `{1, 3, 10, 30} → {0, ⅓, ⅔, 1}`.

**`winsorize(x, p)`** - clip to the group's `[p, 1−p]` quantiles; standard pre-processing before z-scoring heavy-tailed ratios:

```trail
z_clean = zscore(winsorize(accruals_ratio, 0.01))
```

**`xs_mean(x)`, `xs_median(x)`, `xs_sum(x)`** - reduce the group to one value and **broadcast it back** to every member cell.

**`xs_std(x)` / `xs_var(x)` / `xs_min(x)` / `xs_max(x)` / `xs_count(x)` / `xs_quantile(x, q)`** - group standard deviation / variance / min / max / non-null count / q-quantile, each broadcast back to every member (the reducers behind `demean`, `robust_zscore`, `minmax`, … in §8.8).

**`xs_frac(cond)`** - fraction of the group where `cond` is true, broadcast back. Market breadth:

```
cond: {AAA: true, BBB: false, CCC: true, DDD: false} → xs_frac = 0.5 for every entity
```

```trail
signal breadth on us_main at monthly =
    xs_frac(price.adj_close > roll_mean(price.adj_close, 10))
```

Because `xs_*` values depend on the entire group, changing universe membership changes every dependent cell - implementations may not cache them across universe edits.

### 7.3 Elementwise functions (E)

| Function | Semantics | Example |
|---|---|---|
| `sqrt(x)` | null for `x < 0` | `graham = sqrt(22.5 * eps * bvps)` |
| `abs(x)` | absolute value | |
| `log(x)` | natural log; null for `x <= 0` | |
| `exp(x)` | eˣ | `o_prob = exp(o) / (1 + exp(o))` |
| `clamp(x, lo, hi)` | clip to `[lo, hi]`; `lo`/`hi` literals | `exposure clamp(0.15 / vol, 0, 1)` |
| `min(a, b)` / `max(a, b)` | cell-wise pair min/max | `min(r - target, 0)` (downside leg) |
| `sin`/`cos`/`tan`, `asin`/`acos`/`atan(x)` | trigonometry (radians) - transcendental primitives | |
| `floor`/`ceil`/`round(x)` | round to integer | |
| `count(b1, …, bk)` | sum of boolean panels as integers (k ≥ 1); null flags propagate null (§4.3) | Piotroski: `count(f1, …, f9)` |

Bare-literal arguments to these scalar functions are lifted to constants (`log(10)` is valid). Non-transcendental scalar helpers (`log10`, `sigmoid`, `sign`, `hypot`, `signed_log`, …) are **derived** functions in the standard library (§8.8), not primitives.

### 7.4 The negative-value shift rule

For `cagr`/`increase` with `start = lag(x, n)` and `end = x`:

- if `start < 0 < end`: `start' = −start`, `end' = end + 2·(−start)`
- if `start > 0 > end`: `end' = −end`, `start' = start + 2·(−end)`
- otherwise unchanged.

Rationale: preserves growth-direction semantics across sign changes instead of yielding nonsense from negative bases. Example: earnings going −10 → 60 over 3 periods reads as +100 %/yr growth, not as an undefined root of a negative ratio.

### 7.5 Model-context functions (M)

**`weighted_score()`** - legal only as the complete right-hand side of a model statement. Over the model's `score` declarations `(sᵢ, wᵢ)`, with `maxᵢ` = the maximum of scoreᵢ's literal case/else values:

```
numerator   = Σ coalesce(sᵢ · wᵢ, 0)
denominator = Σ dᵢ      where dᵢ = wᵢ·maxᵢ  if sᵢ non-null   (on_missing skip)
                               dᵢ = wᵢ·maxᵢ  always           (on_missing zero)
result      = numerator / denominator      (null if denominator = 0)
```

**Worked example.** Scores: `s1` (cases 2/1/`else 0`, weight 3, max 2) and `s2` (case 1/`else 0`, weight 1, max 1):

| cell | s1 | s2 | skip | zero |
|---|---|---|---|---|
| best | 2 | 1 | (6+1)/(6+1) = **1.00** | 1.00 |
| mid | 1 | 0 | (3+0)/7 ≈ **0.43** | 0.43 |
| s2 unavailable | 2 | null | 6/6 = **1.00** | 6/7 ≈ 0.86 |

`skip` renormalizes so data gaps don't penalize; `zero` treats absence as failure. Choose per model with `on_missing`.

### 7.6 Registered functions *(phase 2)*

Deployment-whitelisted, kind-typed, vectorized host functions - the escape hatch for math outside panel algebra (multivariate regression residuals, DCF table models). Calls are grammatically ordinary; §11 specifies the ABI. Standard packs: statistical (`ols_residual`, `ff3_residual`) and valuation (`dcf_two_stage`, `gurufocus_projected_fcf`, `peter_lynch_fair_value`, `growth_factor`).

```trail
export ivol = roll_std(ff3_residual(price.return, 36), 36)
```

### 7.7 Frequency alignment and the aggregation library

Cross-frequency transforms (§4.4) are ordinary calls that align a field from its native frequency onto the block's target grid:

- **`resample(x, freq, agg)`** - re-bucket `x` to `freq`, reducing each target bucket with `agg` (downsampling; `freq`/`agg` are literals).
- **`to_annual(x)`, `to_quarterly(x)`, `to_monthly(x)`, `to_daily(x)`** - sugar for `resample`, `agg` defaulting to the field's kind rule (§4.2) unless a second argument overrides.
- **`asof(x)`** - upsample by carrying the last known value forward (backward as-of join): the safe coarse-to-fine rule.
- **`ttm(x)` / `trailing(x, "1y")`** - trailing-window transform, kind-aware (rolling `flow` **sum**, `stock` **last**). `sply(x)` is same-period-last-year.
- **Duration windows** - every `roll_*` reducer accepts a duration string (`"1y"`, `"90d"`, `"4q"`) as its window in addition to an integer count.

The **aggregation library** supplies the `agg` argument (the reduction applied to a downsample bucket, a list of values):

| group | reductions |
|---|---|
| basic | `sum`, `mean`, `last`, `first`, `min`, `max`, `count` |
| distribution | `median`, `std`, `var`, `skew`, `kurtosis`, `quantile(q)`, `range` |
| multiplicative | `prod`, `compound` (`prod(1+x)-1`), `geomean` |
| change | `change` (last-first) |

`kind` selects the default; any library reduction overrides it - e.g. `resample(price.adj_close, "monthly", "max")` for a monthly high, `resample(price.return, "annual", "std")` for realized annual volatility. New reductions are named aggregations, not new syntax.

---

## 8. Declarations

A program is one or more declarations. Universe/model/signal/strategy names share one program-level namespace; redeclaring a name is `E-NAME-REBOUND`. Declaration order does not matter for cross-declaration references; assignment order matters *within* a model.

### 8.1 `import` *(inclusion: phase 2)*

```trail
import "metrics/base.trail"
```

Textual inclusion relative to the importing file; the included declarations behave as if written in place. Import cycles are `E-IMPORT-CYCLE`; importing the same file twice along different paths is permitted and idempotent.

### 8.2 `universe`

```
universe NAME = root [where expr]
```

`root` is `stocks` (the merged canonical listing), a pinned listing (`fmp.stocks`), or **another universe's name** - universes compose:

```trail
universe us_main = stocks where meta.exchange in ("NYSE", "NASDAQ") and meta.is_active
universe nonfin  = us_main where meta.sector != "Financials"
universe liquid  = nonfin where meta.market_cap > 200e6
```

The `where` expression is an ordinary boolean expression over schema fields (and, phase 2, cross-model exports - `sharia.compliant`). Membership is evaluated per period (§4.6).

### 8.3 `model`

```
model NAME [on UNIVERSE] [at FREQ] {
    [desc STRING]
    [on_missing skip|zero|median]
    (assignment | score | export)+
}
```

Defaults: `at annual`; `on_missing skip`. `on` may be omitted when the program declares **at most one** universe: with exactly one, that universe is bound; with none, the model runs over the full panel (useful for scratch scripts and fixtures). Omitting `on` while multiple universes are declared is `E-UNIVERSE-UNKNOWN`.

**Assignments** - `name = expr` binds a panel visible to *later* statements in the same model. Top-to-bottom scoping; forward references are `E-NAME-UNDEFINED`; rebinding is `E-NAME-REBOUND`.

**`export name = expr`** - an assignment that is also materialized: it appears in the model's output and (phase 2) is addressable program-wide as `MODEL.name`. Exports are the model's only externally visible effect.

**`score name weight N { … }`** - ordered, first-match-wins cases ending in a mandatory `else`:

```trail
score revenue_growth_score weight 7 {
    2 if revenue_cagr > 0.15
    1 if revenue_cagr > 0.05
    else 0
}
```

Per cell: cases are tested top to bottom; the first true condition's value is the result; null conditions do not match (§4.3 rule 4); if none match, the `else` value; and if *every* condition is null the score is null (§4.3 rule 4, all-null case). Case values and the `else` value MUST be non-negative numeric literals - enforced at parse time (a non-literal there is a syntax error, not a deferred diagnostic). Numeric-literal values are what let `weighted_score()` compute each score's maximum statically. Conditions are arbitrary boolean expressions, including references to other scores or macro series (floating hurdles, §4.1). `weight` is metadata: it does not affect the score panel itself, only `weighted_score()` and phase-4 weight learning, where declared weights are **priors** that a learned weight table may override without touching source.

A score declaration binds its name like an assignment: later statements may reference it.

**Complete model example** (annual, with intermediate names, flags, checklist, z-composite, and weighted rollup):

```trail
model fundamentals on nonfin at annual {
    desc "Growth + quality with checklist and composite"
    on_missing skip

    revenue_cagr = cagr(income.revenue, 4)
    score growth_score weight 7 { 2 if revenue_cagr > 0.15; 1 if revenue_cagr > 0.05; else 0 }

    roa       = income.net_income / avg2(balance.total_assets)
    f_roa_pos = roa > 0
    f_cfo_pos = cash.cfo > 0
    f_accrual = cash.cfo > income.net_income
    export checklist = count(f_roa_pos, f_cfo_pos, f_accrual)

    gross_profitability = (income.revenue - income.cogs) / balance.total_assets
    export quality_z = ( zscore(gross_profitability) by meta.sector
                       + zscore(roa) by meta.sector ) / 2

    export composite = weighted_score()
}
```

Output panel columns: `entity`, `period`, `checklist`, `quality_z`, `composite`.

### 8.4 `signal`

```
signal NAME [on UNIVERSE] [at FREQ] = expr
```

Sugar for a model with a single export of the same name:

```trail
signal value_composite on nonfin at annual =
    ( zscore(-pe) + zscore(-pb) + zscore(-ev_ebitda) ) / 3
```

is equivalent to `model value_composite on nonfin at annual { export value_composite = … }`.

### 8.5 `strategy` *(execution: phase 3)*

```
strategy NAME {
    universe NAME
    signal expr
    rebalance annual|quarterly|monthly
    select top N [where expr]
    weighting equal|value|signal
    [hold_band LO .. HI]
    [gate expr]
    [fallback cash|tbills|NAME]
    [exposure expr]
    [costs NAME]
}
```

Field semantics:

| Field | Meaning | Default |
|---|---|---|
| `universe` | selection pool, point-in-time membership | required |
| `signal` | ranking expression (higher = better); may reference model exports | required |
| `rebalance` | evaluation schedule | required |
| `select top N [where c]` | take best N by signal after filtering by `c` | required |
| `weighting` | `equal` \| `value` (by `meta.market_cap`) \| `signal` (proportional) | `equal` |
| `hold_band LO .. HI` | hysteresis: a current holding is kept while its rank stays within `HI × N`; a new name enters only if ranked within `LO × N` - cuts churn at the boundary | none |
| `gate` | broadcast boolean; when false the entire book moves to `fallback` | always-on |
| `fallback` | `cash` (0 return) \| `tbills` (accrues `macro.risk_free`) \| a declared index | `cash` |
| `exposure` | per-period equity fraction, clamped to [0,1]; remainder in `fallback` | `1` |
| `costs` | named engine cost model | engine default |

**Execution timeline** (normative). At each rebalance date `t`:

1. Reconstruct `universe` membership as of `t` (PIT, delisted names included for their live periods).
2. Evaluate `gate` at `t`; if false → the entire book is `fallback`; done.
3. Evaluate `signal` at `t`; apply `select`'s `where`; take `top N` with `hold_band` hysteresis against current holdings.
4. Weight per `weighting`, scale by `exposure(t)`, book `costs`.

**Example - trend-gated momentum (Faber filter + vol scaling):**

```trail
strategy trend_momentum {
    universe  us_main
    signal    momentum.mom_12_1
    rebalance monthly
    select    top 50 where price.adj_close > 5
    weighting equal
    hold_band 0.8 .. 1.2
    gate      index.spx.close > roll_mean(index.spx.close, 10)
    fallback  tbills
    exposure  clamp(0.15 / roll_std(index.spx.return, 12), 0, 1)
}
```

### 8.6 `backtest` *(execution: phase 3)*

```
backtest STRATEGY from DATE to DATE {
    benchmark dotted
    pit_lag DURATION
    report NAME ("," NAME)*
}
```

```trail
backtest trend_momentum from 2010-01 to 2025-12 {
    benchmark index.spx
    pit_lag   45d
    report    cagr, sharpe, sortino, max_drawdown, calmar, var_95, cvar_95, turnover, deflated_sharpe
}
```

`pit_lag` sets the filing-date lag used for all PIT alignment (§4.4) in this run. Report metrics are engine-computed over the simulated return stream - portfolio-level risk metrics live here, while §7.1's operators build per-entity *features*.

### 8.7 `learn` *(execution: phase 4)*

```
learn weights for MODEL {
    segment by dotted ("," dotted)*
    target expr
    method NAME
    validate call
}
```

```trail
learn weights for fundamentals {
    segment  by meta.country, meta.industry_group
    target   fwd_return(12m)              # the ONLY context where fwd_return is legal
    method   shrink_to_equal
    validate purged_kfold(5, embargo = 3m)
}
```

Semantics: per segment, estimate score weights against the forward-return target under the named method, validated as declared; output is a **weight table** (data, not code) the runtime may bind in place of the model's `weight` priors. Method and validation vocabularies are engine-defined *(finalized with phase 4)*.

### 8.8 `def` - user and standard-library functions

```
def NAME "(" [NAME ("," NAME)*] ")" "=" expr
```

```trail
def gross_margin(gross_profit, revenue) = gross_profit / revenue
def sharpe(r, n)                        = roll_mean(r, n) / roll_std(r, n)
```

A `def` binds a **non-recursive expression macro**. It is not a runtime function: at every call site the argument expressions are substituted for the parameters in the body, and the resulting expression is compiled inline (§10). Normative rules:

1. **Body is a single expression** over the parameters, schema fields, primitives, and other functions. No statements, no local bindings, no side effects.
2. **Non-recursive.** A function that calls itself directly or transitively is a compile error (`E-FUNC-RECURSION`); the call graph MUST be acyclic. This is what preserves totality (I2).
3. **Composition only.** A `def` may compose primitives and other functions; it cannot introduce a new primitive (a windowing or cross-sectional operation not already available). Such needs are registered functions (§7.6), not `def`s.
4. **Arity is exact** (`E-FUNC-ARITY`); no keyword arguments, no defaults, no overloading.
5. **Hygiene.** Substitution replaces only parameter references; a function body does not capture names from the caller's model scope.
6. **Static-argument propagation (I3).** A parameter that flows into a window/quantile position must receive a numeric literal at the call site, so the inlined expression still has static windows.
7. **Definition sites.** `def`s are top-level declarations valid in a model file or a library file; they are removed from the program once inlined. The bundled standard library and user libraries are `.trail` files of `def`s brought in by `import` (§8.1).

Because the derived layer is expressible this way, most of the function catalog - financial ratios, `beta`/`yoy`/`avg2`, hyperbolics, `sigmoid`/`signed_log`, finite-difference calculus, robust/rolling statistics, published factors - is Trail source in the standard library rather than engine code; the engine carries only the primitives (§7) and registered functions (§7.6). The bundled library ships as `stdlib/{math,stats,transform,calculus,geometry,factor,timeseries,core}.trail` and is **implicitly loaded** by the pipeline (the CLI `--no-stdlib` opts out); `docs/function-catalog.md` classifies the full surface (primitive / derived / registered). The `timeseries` module holds the derived operators migrated out of the engine (`yoy`, `avg2`, `cagr`, `beta`, `pctile`, …); `factor` holds the cross-sectional factor toolkit (`ntile`, `scale`, `neutralize`, `xs_corr`, …). Discovery (§1.3) tags each function `primitive` or `derived`.

---

## 9. Diagnostics

Validators MUST report at minimum the following. Errors block compilation; warnings do not. `trail validate` exits 0 iff no errors.

| Code | Severity | Phase | Condition | Trigger example |
|---|---|---|---|---|
| `E-FIELD-UNKNOWN` | error | 1 | field/`by` target not in schema | `income.bogus` |
| `E-FUNC-UNKNOWN` | error | 1 | function neither built-in nor registered | `frobnicate(x)` |
| `E-FUNC-ARITY` | error | 1 | wrong positional argument count | `lag(x)` |
| `E-NAME-UNDEFINED` | error | 1 | name used before assignment in its model | `a = b + 1` with no `b` |
| `E-NAME-REBOUND` | error | 1 | name reused within a model, or duplicate top-level declaration | two `model quality` decls |
| `E-SCORE-LITERAL` | error (parse) | 1 | score case/else value not a numeric literal - rejected by the grammar (surfaces as a syntax error) | `x if c else 0` in a score block |
| `E-FWD-CONTEXT` | error | 1 | `fwd_return` outside `learn.target` | `a = fwd_return(12m)` |
| `E-UNIVERSE-UNKNOWN` | error | 1 | `on` names an undeclared universe (or omitted with ≠1 universe) | `model m on nowhere` |
| `E-SOURCE-UNKNOWN` | error | 1 (config) / 2 (pins) | pin or precedence names an undeclared source | `x @ nosuch` |
| `E-SOURCE-DRIVER` | error | 1 (config) | driver is neither a registered `trail.sources` entry point nor a resolvable dotted path | `driver: nosuch` |
| `E-SOURCE-PANEL` | error | 1 | source panel lacks `entity`/`time`, or (under `panel.strict`) any contract deviation | |
| `W-UPSAMPLE-FLOW` | warning | 1 | a `flow`/`return` field upsampled by as-of (repeating a total mis-scales it; resample explicitly) | `income.revenue` at `daily` |
| `W-SOURCE-PANEL` | warning | 1 | non-strict: source panel deviated from the contract and was coerced | |
| `E-PIN-UNSUPPORTED` | error | 1 only | any source pin before phase 2 | `x @ fmp` |
| `E-IMPORT-CYCLE` | error | 2 | import cycle | a imports b imports a |
| `E-FUNC-RECURSION` | error | 1 | a `def` calls itself directly or transitively | `def f(x) = f(x)` |
| `E-FUNC-DUP` | error | 1 | two `def`s share a name | - |
| `W-MEDIAN-DEFERRED` | warning | 1 only | `on_missing median` (treated `skip`) | |
| `W-PERIOD-DEFERRED` | warning | 1 only | a non-annual `at` frequency while the implementation still runs single-frequency (no resampling yet) | `model m at monthly { ... }` |
| `W-KIND-STOCK-FLOW` | warning | 1 | bare `stock`/`flow` division without `avg2`/`lag` | `income.cogs / balance.inventory` |

Reserved for future standardization: `E-TYPE-ORDER` (ordered comparison on strings), `E-ARG-STATIC` (non-literal window arguments).

---

## 10. Runtime configuration (`trail.yaml`)

The CLI binds programs to data through a YAML file. Resolution order: `--config PATH` flag → `./trail.yaml` → built-in default (bundled fixture source). A missing config file is **not** an error - `trail run` works out of the box and in CI.

### 10.1 Schema

```yaml
# trail.yaml
panel:
  periods: [2015, 2025]          # optional time bounds (fiscal years or ISO dates)
  frequency: annual              # optional target frequency; default = finest referenced source
  strict: false                  # true = a non-conforming source panel is a hard error

sources:                         # name -> driver binding; keys are the language-visible
  fixture:                       # source names used by '@' pins
    driver: fixture              # a registered trail.sources name, or a dotted path
  fmp:
    driver: trail.sources.aiofmp_cache      # phase 2
    options:
      cache_path: ~/aiofmp-cache
      api_key_env: FMP_API_KEY              # env var NAME - never the secret itself
  edgar:
    driver: edgar                           # registered by `pip install trail-edgar`
    options:
      identity: "name contact@example.com"  # SEC fair-access User-Agent
      tickers: [AAPL, MSFT]

precedence:                      # namespace -> ordered source names (per-cell first-non-null)
  default: [fmp]
  statements: [edgar, fmp]       # phase 2: per-namespace chains
  price: [fmp]
```

### 10.2 Normative rules

1. **Driver contract.** A driver resolves to a `factory(options: dict) -> DataSource`, either by a registered name (Python entry-point group `trail.sources`, so `pip install trail-<name>` exposes `driver: <name>`) or by a dotted import path; registered names take precedence. A `DataSource` implements one required method, `load(fields: set[str], *, periods=None) -> panel`, returning the long-format panel (§4.1) for the requested schema columns. It MAY also implement the extended-tier capabilities - field discovery, universe enumeration, and a capabilities descriptor - which `trail catalog` and (phase 2) multi-source routing use when present. An unresolvable driver is a startup configuration error (`E-SOURCE-DRIVER`), not a query-time error.
2. **Precedence.** `precedence.default` is required (inferred as "all declared sources, declaration order" only when `precedence` is entirely absent). Namespace keys override `default`. Every source named in any chain MUST exist under `sources` (`E-SOURCE-UNKNOWN`). Phase 1 supports exactly one effective source (the first of `default`); per-cell multi-source coalescing is phase 2.
3. **Secrets** are referenced by environment-variable name (`api_key_env`); configurations containing literal secrets SHOULD be rejected by tooling.
4. **Panel conformance.** A returned panel MUST carry `entity` and `time` columns; their absence is always `E-SOURCE-PANEL` (nothing can be coerced). Other deviations - a missing requested field, a `time` not typed as a timestamp, or a column outside the schema - are `E-SOURCE-PANEL` under `panel.strict: true`, otherwise `W-SOURCE-PANEL` with coercion: columns outside the schema are dropped, `time` is cast to a period-end timestamp, and missing requested fields are added as all-null columns. `panel.strict` defaults to `false`; production configurations SHOULD set it `true`.
5. **Pluggable schema.** A source package MAY extend the canonical field vocabulary by contributing fields under the `trail.schema` entry-point group; each entry point resolves to a mapping of dotted column to kind (e.g. `{"gmd.rGDP": "level", "gmd.infl": "rate"}`). Contributions merge with the built-in fields into the *active schema* (built-in wins on collision) that validation, `trail catalog`, and panel conformance use. Field kinds are freeform strings identifying the measure (`level`, `rate`, `index`, `ratio`, ...); only `flow` and `stock` carry special meaning (the `W-KIND-STOCK-FLOW` lint). Contributing the vocabulary is independent of a source instance advertising which of those fields it actually serves (the discovery capability).
6. **Pins ↔ config.** `@ name` in programs resolves against `sources` keys - configuration is what gives pin names meaning. Dependency extraction (I3) reports pinned fields per source so the runtime can prefetch exactly what a program needs.
7. **Frequency alignment.** Each source declares a native frequency (its capabilities descriptor). The runtime aligns every source panel to the model's target frequency (§4.4) - downsample by kind or upsample by as-of - and merges the aligned panels on `(entity, time)`.
8. **`panel.periods`** bounds the `time` axis after loading (years or ISO dates); **`panel.frequency`** sets the default target frequency (else finest referenced). Neither changes PIT semantics.
9. `trail validate` is config-free (pure static analysis); only `trail run`/`backtest` read the config.

---

## 11. Registered function ABI *(phase 2)*

A registered function declares: a **name**, positional **parameter kinds**, a **return kind**, and a vectorized host implementation. Registration is deployment configuration (an allow-list), not program text; agents may propose functions, humans review the host code.

```python
@trail_function(returns="ratio")
def ff3_residual(returns: Kind.ratio, window: Kind.count) -> Kind.ratio:
    """Rolling Fama-French 3-factor regression residual, per entity."""
    ...  # columnar implementation; per-row Python is a conformance violation (I5)
```

The validator treats registered names exactly like built-ins (arity, kind lints, I3 static-window rules). Implementations MUST reject a registered function whose declared signature and host signature disagree.

---

## 12. Grammar (normative)

```lark
// file grammar (model files, agent-authored artifacts)
start: decl+
// interactive dialect (REPL / notebooks); a strict superset - meta-command, decl, or bare expr
repl_line: meta_command | decl | expr
meta_command: "?"            -> meta_catalog
            | "?" dotted     -> meta_describe   // ?income, ?income.revenue, ?cagr, ?functions, ...
?decl: import_decl | func_def | universe_decl | model_decl | signal_decl
     | strategy_decl | backtest_decl | learn_decl

import_decl: "import" STRING
func_def: "def" NAME "(" [NAME ("," NAME)*] ")" "=" expr
universe_decl: "universe" NAME "=" dotted ("where" expr)?
model_decl: "model" NAME ("on" NAME)? ("period" PERIOD)? "{" model_stmt+ "}"
?model_stmt: "desc" STRING                  -> desc_stmt
           | "on_missing" POLICY            -> policy_stmt
           | "export" NAME "=" expr         -> export_stmt
           | "score" NAME "weight" NUMBER "{" score_case+ "else" NUMBER "}" -> score_stmt
           | NAME "=" expr                  -> assign_stmt
score_case: NUMBER "if" expr        // value is a numeric literal (LALR-clean; avoids the ternary `if` conflict)
signal_decl: "signal" NAME ("on" NAME)? ("period" PERIOD)? "=" expr

strategy_decl: "strategy" NAME "{" strat_field+ "}"
?strat_field: "universe" NAME | "signal" expr | "rebalance" FREQ
            | "select" "top" NUMBER ("where" expr)? | "weighting" WEIGHTING
            | "hold_band" NUMBER ".." NUMBER | "costs" NAME
            | "gate" expr | "fallback" NAME | "exposure" expr
backtest_decl: "backtest" NAME "from" DATE "to" DATE "{" bt_field+ "}"
?bt_field: "benchmark" dotted | "pit_lag" DURATION | "report" NAME ("," NAME)*
learn_decl: "learn" "weights" "for" NAME "{" learn_field+ "}"
?learn_field: "segment" "by" dotted ("," dotted)* | "target" expr
            | "method" NAME | "validate" expr

?expr: ternary
?ternary: or_e ("if" or_e "else" ternary)?
?or_e: and_e ("or" and_e)*
?and_e: not_e ("and" not_e)*
?not_e: "not" not_e | cmp
?cmp: coal (CMP_OP coal)? | coal "in" "(" literal ("," literal)* ")"
?coal: sum ("??" sum)*
?sum: prod (SUM_OP prod)*
?prod: pow_ (MUL_OP pow_)*
?pow_: unary ("^" pow_)?
?unary: "-" unary | pinned
?pinned: atom ("@" NAME)?
?atom: call | ref | literal | "(" expr ")"
call: NAME "(" [arg ("," arg)*] ")" ("by" dotted)?
?arg: NAME "=" expr | expr
ref: NAME ("." NAME)*
dotted: NAME ("." NAME)*
?literal: NUMBER | STRING | "true" | "false"

CMP_OP: "==" | "!=" | ">=" | "<=" | ">" | "<"
SUM_OP: "+" | "-"
MUL_OP: "*" | "/" | "%"
PERIOD: "annual" | "quarterly" | "monthly" | "daily"   // one terminal for model period and strategy rebalance; model semantics use annual/quarterly/monthly
FREQ: PERIOD
POLICY: "skip" | "zero" | "median"
WEIGHTING: "equal" | "value" | "signal"
NUMBER: /[0-9][0-9_]*(\.[0-9]+)?([eE][+-]?[0-9]+)?/
STRING: /"[^"]*"/
DATE: /\d{4}-\d{2}(-\d{2})?/
DURATION: /\d+[dmy]/
%import common.CNAME -> NAME
%import common.WS
%ignore WS
%ignore /#[^\n]*/
```

Implementations MUST parse with a deterministic algorithm (LALR(1) or equivalent); grammar ambiguity is an implementation defect, not a program error.

---

## Appendix A - Reserved words

See §3.2. Machine-readable list:

```
and annual at backtest by cash costs daily def else equal export exposure
fallback false for from gate hold_band hourly if import in learn median minute
model monthly not on on_missing or pit_lag quarterly rebalance report score
select signal skip strategy tbills to top true universe validate value weekly
weight weighting weights where zero
```

## Appendix B - Deferred-construct behavior by phase

Phase-1 implementations MUST behave as follows: source pins → `E-PIN-UNSUPPORTED`; `sply`/`ttm`/`roll_tail_mean`/registered names → `E-FUNC-UNKNOWN`; `on_missing median` → `W-MEDIAN-DEFERRED` (treated `skip`); cross-model export references → `E-FIELD-UNKNOWN`; `import`/`strategy`/`backtest`/`learn` → parsed; attempting to *execute* them exits with a clear phase error.

## Appendix C - Complete annotated example

```trail
# ---------- universes ----------
universe us_main = stocks
    where meta.exchange in ("NYSE", "NASDAQ") and meta.is_active and meta.market_cap > 200e6
universe nonfin = us_main where meta.sector != "Financials"

# ---------- Piotroski F-Score ----------
model piotroski on nonfin at annual {
    desc "Piotroski F-Score: nine binary fundamental-strength signals"

    roa        = income.net_income / avg2(balance.total_assets)
    cfo_assets = cash.cfo / avg2(balance.total_assets)
    ltd_ratio  = balance.long_term_debt / avg2(balance.total_assets)
    cur_ratio  = balance.current_assets / balance.current_liabilities
    gm         = income.gross_profit / income.revenue
    turnover   = income.revenue / avg2(balance.total_assets)

    f_roa_pos  = roa > 0                                # profitable
    f_cfo_pos  = cash.cfo > 0                           # cash-generative
    f_droa     = roa > lag(roa, 1)                      # improving returns
    f_accrual  = cfo_assets > roa                       # earnings backed by cash
    f_leverage = ltd_ratio < lag(ltd_ratio, 1)          # deleveraging
    f_liquid   = cur_ratio > lag(cur_ratio, 1)          # improving liquidity
    f_noissue  = (cash.stock_issued ?? 0) == 0          # no dilution (null-safe)
    f_margin   = gm > lag(gm, 1)                        # improving margins
    f_turnover = turnover > lag(turnover, 1)            # improving efficiency

    export fscore = count(f_roa_pos, f_cfo_pos, f_droa, f_accrual, f_leverage,
                          f_liquid, f_noissue, f_margin, f_turnover)   # 0..9
}

# ---------- value signal (phase-2 cross-model refs shown for completeness) ----------
signal cheap on nonfin at annual =
    zscore(-(price.adj_close / income.eps_diluted))     # cheaper = higher

# ---------- strategy + backtest (phase 3) ----------
strategy quality_value {
    universe  nonfin
    signal    cheap + zscore(piotroski.fscore)
    rebalance annual
    select    top 25 where price.adj_close > 5
    weighting equal
    hold_band 0.8 .. 1.2
    gate      index.spx.close > roll_mean(index.spx.close, 10)
    fallback  tbills
}

backtest quality_value from 2010-01 to 2025-12 {
    benchmark index.spx
    pit_lag   45d
    report    cagr, sharpe, max_drawdown, turnover, deflated_sharpe
}
```
