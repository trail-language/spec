# Trail-EDGAR setup + walkthrough (verified notes)

**How to use this guide:**

- **Python >= 3.11** (every command below was verified on CPython 3.13.13).
- Pick a working directory (convention: `trail-work/`) and create the venv **inside** it (`.venv`). Every command runs from inside the working directory with relative paths.
- You need an SEC fair-access identity string (`"Your Name your.email@example.com"`); it appears as the `$EDGAR_IDENTITY` placeholder throughout — substitute the real value in your local files, never commit it.
- Running example throughout: **AAPL + MSFT, fiscal years 2020–2024**, SEC EDGAR via `trail-edgar`.
- Every command was executed and every output block is real (trimmed only where noted), re-verified 2026-10-31 in a fresh venv from PyPI; commands are in portable form so you can follow along and execute them on any platform.

---

## 1. Setup

### Goal
Install `trail-lang` (engine) + `trail-edgar` (SEC EDGAR source driver) from PyPI into an isolated venv so the `edgar.*` namespace works, and verify.

### Command (verified 2026-10-31, fresh venv)
```
python3 -m venv .venv
.venv/bin/pip install trail-lang trail-edgar
```
PyPI versions (verified): `trail-lang 0.18.0`, `trail-edgar 0.5.0`. If your venv has no `pip` module yet: `.venv/bin/python -m ensurepip` first.

**REPL note:** the terminal REPL needs `prompt_toolkit`, which the PyPI 0.18.0 release does **not** declare as the `[repl]` extra — install it directly (the extra arrives with the next release):
```
.venv/bin/pip install prompt_toolkit
```
The REPL itself also has a PyPI-vs-main caveat — read the note at the start of §12 before running that section.

### Verification (verbatim)
```
$ .venv/bin/python -c "import importlib.metadata as m; import trail; print(trail.__version__, m.version('trail-lang'), m.version('trail-edgar'))"
0.18.0 0.18.0 0.5.0
```
- `trail.__version__` reads from the installed package; `trail_edgar` has **no `__version__` attribute** (verified: `AttributeError: module 'trail_edgar' has no attribute '__version__'`) — use `importlib.metadata` or `pip show trail-edgar`.
- `trail --version` does not exist:
  ```
  $ .venv/bin/trail --version
  Usage: trail [OPTIONS] COMMAND [ARGS]...
  Try 'trail --help' for help.

  Error: No such option '--version'.        # exit 2 — not a flag; use the version line above
  ```
- **Import name trap:** the dist is `edgartools==5.62.1` (installed as a dependency) but it does NOT import as `edgartools`:
  ```
  $ .venv/bin/python -c "from edgar import Company; import edgar; print('edgar import OK')"
  edgar import OK
  ```
  The top-level module is **`edgar`** (`from edgar import Company`, `edgar.exceptions.CompanyNotFoundError`). The driver itself uses `from edgar import Company`.
- Without `prompt_toolkit`, the REPL exits early with:
  ```
  $ .venv/bin/trail repl
  prompt_toolkit is required for the REPL.
  Install it with: pip install trail-lang[repl]        # exit 1
  ```

### Minimal config — `trail.yaml` (hand-written)

There is **no `trail init` / scaffold command** (verified: §11 lists every CLI command) — the config is hand-written. Canonical minimal config, one comment per key:

```yaml
# Minimal Trail config: SEC EDGAR source, 2-ticker universe, annual 2020-2024.
sources:
  edgar:
    driver: edgar                      # source driver name (entry point provided by trail-edgar)
    options:
      identity: "$EDGAR_IDENTITY"      # SEC fair-access 'Your Name your.email@example.com'
      tickers: [AAPL, MSFT]            # tickers to fetch
      years: [2020, 2024]              # the N most-recent fiscal years the driver fetches
      cache_dir: .edgar-cache          # local cache dir (relative paths are fine)
precedence:
  default: [edgar]                     # field-namespace -> source resolution order
panel:
  periods: [2020, 2024]                # requested panel window
  pit: auto                            # as-of filing-date placement (see §5)
  strict: false
```

**Identity:** put your fair-access string in `options.identity` (shown here as the `$EDGAR_IDENTITY` placeholder — substitute the real value in your local file). Unix shells may instead export it once and omit the `identity` key: `export EDGAR_IDENTITY="Your Name your.email@example.com"`. Resolution order: `options.identity` first, then the env var; without either you get the coded error in §9.

### What it does
The pip install wires the `edgar` driver in via the entry-point mechanism (the driver registers itself with the engine; no code changes needed); `precedence.default: [edgar]` makes `edgar.*` fields resolve to this source; `panel` defines the requested periods and PIT mode.

### Gotchas
- `trail --version` does not exist; version comes from `import trail` / `importlib.metadata`.
- On PyPI 0.18.0 the `[mcp]` extra is the only extra declared in `trail-lang` (the `trail-lang[repl]` referenced in the REPL error text is **not** declared there — install `prompt_toolkit` directly).

---


## 2. Fetch first frame

### Goal
Smallest run that materializes a frame of `edgar.*` data for the 2-ticker universe.

### Model — `first.trail` (full text)
```
# First frame: one field, one model, no universe declaration (runs over the whole panel).
model rev_frame at annual {
    export rev = edgar.revenue
}
```

### Command (verbatim)
```
.venv/bin/trail run first.trail --model rev_frame --config trail.yaml --out first.csv
```

### Real output
```
wrote first.csv
```
`first.csv` (complete — 9 rows):
```
entity,time,rev
AAPL,2020-12-31T00:00:00.000000,274515000000.0
AAPL,2021-12-31T00:00:00.000000,365817000000.0
AAPL,2022-12-31T00:00:00.000000,394328000000.0
AAPL,2023-12-31T00:00:00.000000,383285000000.0
AAPL,2024-12-31T00:00:00.000000,391035000000.0
MSFT,2021-12-31T00:00:00.000000,168088000000.0
MSFT,2022-12-31T00:00:00.000000,198270000000.0
MSFT,2023-12-31T00:00:00.000000,211915000000.0
MSFT,2024-12-31T00:00:00.000000,245122000000.0
```

### What it does
- Frame = long polars panel `(entity, time, rev)`; one row per (ticker, fiscal year).
- **Time key = Dec 31 of the fiscal-year label.** AAPL FY2024 (ended 2024-09-30) is keyed `2024-12-31`; MSFT FY2024 (ended 2024-06-30) is also keyed `2024-12-31`. Verified against raw edgartools statements: AAPL `FY 2020…FY 2025` Total Revenue = 274.515/365.817/394.328/383.285/391.035B (exactly the 10-K values); MSFT `FY 2021…FY 2026` = 168.088/198.270/211.915/245.122B (+281.724/331.839B for FY2025/26, outside the requested window).
- **MSFT has no 2020 row.** Root cause (verified): edgartools `Company.income_statement(periods=N, period="annual")` returns only the **N most recent fiscal years** (N=6 here, from `year_bounds` on the config). MSFT's 6 most recent are FY2021–FY2026, so requested year 2020 silently falls outside the fetch window. AAPL's window (FY2020–FY2025) covers 2020, so AAPL has all 5 years.

### Gotchas
- `trail run PATH` alone fails: `Error: Missing option '--model'.` — `--model <name>` is required.
- `trail validate PATH` takes NO `--config`: `Error: No such option '--config'.` (exit 2). Validate with `trail validate first.trail` → prints `OK`.
- Requested years outside the driver's fetch window drop **silently** (no warning) — check row counts per ticker.

---

## 3. Calculation on that frame

### Goal
First `.trail` program computing derived metrics on the edgar frame.

### Model — `fundamentals.trail` (full text)
```
# First model on the EDGAR frame: revenue, revenue YoY, gross margin, net margin.
# Runs over the whole loaded panel (no universe declaration) at annual frequency.
model fundamentals at annual {
    rev_yoy = yoy(edgar.revenue)
    gm = gross_margin(edgar.gross_profit, edgar.revenue)
    nm = net_margin(edgar.net_income, edgar.revenue)
    export rev = edgar.revenue
    export rev_yoy          # bare export re-exports the local binding
    export gross_margin = gm
    export net_margin = nm
}
```

### Command (verbatim)
```
.venv/bin/trail run fundamentals.trail --model fundamentals --config trail.yaml --out fundamentals.csv
```

### Real output
```
wrote fundamentals.csv
```
`fundamentals.csv` (complete — 9 rows):
```
entity,time,rev,rev_yoy,gross_margin,net_margin
AAPL,2020-12-31T00:00:00.000000,274515000000.0,,0.38233247727810865,0.20913611278072236
AAPL,2021-12-31T00:00:00.000000,365817000000.0,0.33259384733074704,0.4177935962516778,0.2588179335569424
AAPL,2022-12-31T00:00:00.000000,394328000000.0,0.0779378760418461,0.43309630561360085,0.2530964070519973
AAPL,2023-12-31T00:00:00.000000,383285000000.0,-0.02800460530319937,0.4413112957720756,0.2530623426432028
AAPL,2024-12-31T00:00:00.000000,391035000000.0,0.02021994077514111,0.4620634981523393,0.23971255769943867
MSFT,2021-12-31T00:00:00.000000,168088000000.0,,0.689258007710247,0.36451739564989766
MSFT,2022-12-31T00:00:00.000000,198270000000.0,0.17956070629670173,0.684016744842891,0.3668633681343622
MSFT,2023-12-31T00:00:00.000000,211915000000.0,0.06882029555656421,0.6892008588349102,0.3414623787839464
MSFT,2024-12-31T00:00:00.000000,245122000000.0,0.1566996201307127,0.6976444382797138,0.35955972944084985
```

Also verified:
```
$ .venv/bin/trail validate fundamentals.trail
OK
$ .venv/bin/trail describe fundamentals.trail
Panel: 9 rows | 2 entities | 44 fields | period 2020-12-31..2024-12-31

Fields by namespace:
  edgar (40): edgar.accounts_payable, edgar.accounts_receivable, edgar.capex, edgar.cash_and_equivalents,
    edgar.cash_and_short_term_investments, edgar.cff, edgar.cfi, edgar.cfo, edgar.cogs, edgar.common_stock,
    edgar.current_assets, edgar.current_liabilities, edgar.depreciation_amortization, edgar.dividends_paid,
    edgar.ebitda, edgar.eps_diluted, edgar.free_cash_flow, edgar.goodwill, edgar.gross_profit,
    edgar.income_before_tax, edgar.income_tax_expense, edgar.interest_expense, edgar.inventory,
    edgar.long_term_debt, edgar.minority_interest, edgar.net_change_in_cash, edgar.net_fixed_assets,
    edgar.net_income, edgar.operating_income, edgar.other_current_assets, edgar.retained_earnings,
    edgar.revenue, edgar.sga, edgar.stock_issued, edgar.total_assets, edgar.total_debt, edgar.total_equity,
    edgar.total_liabilities, edgar.weighted_average_shares, edgar.weighted_average_shares_diluted
  meta (4): meta.country, meta.exchange, meta.is_active, meta.sector
...
  meta.exchange (1 distinct):
      Nasdaq  9
  meta.sector (2 distinct):
      Electronic Computers           5
      Services-Prepackaged Software  4
```

### What it does
Local bindings (no `export`) are intermediate; `export` selects output columns. `yoy(x)` is the stdlib one-arg YoY (it wraps `lag(x, 1)`). First available year has no lag → `rev_yoy` is null (empty CSV cell). `meta.*` fields (exchange/sector/is_active/country) are current attributes, not filing-dated.

### Gotchas
- `yoy` on the first year of an entity is null — expected, not a fetch failure.
- `describe` reports the panel as "44 fields" (the 40 edgar + meta vocabulary, not just the 4 exported columns).

---

## 4. Functions (per-feature examples, same running example)

### Goal
Exercise each function family meaningful for edgar data, one small example each, on the same 2-ticker annual frame.

### Model — `functions.trail` (full text)
```
# One small example per function family, on the same 2-ticker annual frame.
model functions at annual {
    # time-series (per entity)
    cfo_lag2  = lag(edgar.cfo, 2)
    rev_ttm   = ttm(edgar.revenue)            # kind-aware desugar: flow -> trailing 4-period sum
    rev_roll3 = roll_mean(edgar.revenue, 3)
    rev_cagr3 = cagr(edgar.revenue, 3)        # stdlib timeseries.trail
    cfo_cum   = cumsum(edgar.cfo)
    rev_tsavg = ts_mean(edgar.revenue)        # whole-series mean per entity
    rev_dd    = drawdown(edgar.revenue)       # stdlib: x / cummax(x) - 1
    # cross-sectional (per period, across the 2 entities)
    rev_rank   = rank(edgar.revenue)
    rev_zscore = zscore(edgar.revenue)
    rev_xsmean = xs_mean(edgar.revenue)
    rev_pctile = pctile(edgar.revenue)
    # elementwise / null semantics
    cogs_pct  = edgar.cogs / edgar.revenue    # '/' lowers to safe_div: 0/0 or x/0 -> null
    log_rev   = log(edgar.revenue)
    export cfo_lag2
    export rev_ttm
    export rev_roll3
    export rev_cagr3
    export cfo_cum
    export rev_tsavg
    export rev_dd
    export rev_rank
    export rev_zscore
    export rev_xsmean
    export rev_pctile
    export cogs_pct
    export log_rev
}
```

### Command (verbatim)
```
.venv/bin/trail run functions.trail --model functions --config trail.yaml --out functions.csv
```
Output: `wrote functions.csv`. `functions.csv` (complete — 9 rows; values in raw form, e.g. 2.718… = log of 15B):
```
entity,time,cfo_lag2,rev_ttm,rev_roll3,rev_cagr3,cfo_cum,rev_tsavg,rev_dd,rev_rank,rev_zscore,rev_xsmean,rev_pctile,cogs_pct,log_rev
AAPL,2020-12-31T00:00:00.000000,,274515000000.0,,,80674000000.0,361796000000.0,0.0,1.0,,274515000000.0,,0.6176675227218913,26.338271741211766
AAPL,2021-12-31T00:00:00.000000,,365817000000.0,,,184712000000.0,361796000000.0,0.0,2.0,0.7071067811865475,266952500000.0,1.0,0.5822064037483222,26.625399045306096
AAPL,2022-12-31T00:00:00.000000,80674000000.0,394328000000.0,344886666666.6667,,306863000000.0,361796000000.0,0.0,2.0,0.7071067811865476,296299000000.0,1.0,0.5669036943863991,26.700448887228625
AAPL,2023-12-31T00:00:00.000000,104038000000.0,383285000000.0,381143333333.3333,0.1176828346030312,417406000000.0,361796000000.0,-0.02800460530319937,2.0,0.7071067811865476,297600000000.0,1.0,0.5586887042279244,26.672044674729445
AAPL,2024-12-31T00:00:00.000000,122151000000.0,391035000000.0,389549333333.3333,0.02247001899501888,535660000000.0,361796000000.0,-0.008350915988720065,2.0,0.7071067811865476,318078500000.0,1.0,0.5379365018476607,26.692062906992128
MSFT,2021-12-31T00:00:00.000000,,168088000000.0,,,76740000000.0,205848750000.0,0.0,1.0,-0.7071067811865475,266952500000.0,0.0,0.31074199228975297,25.847753488733158
MSFT,2022-12-31T00:00:00.000000,,198270000000.0,,,165775000000.0,205848750000.0,0.0,1.0,-0.7071067811865476,296299000000.0,0.0,0.315983255157109,26.01289557509688
MSFT,2023-12-31T00:00:00.000000,76740000000.0,211915000000.0,192757666666.66666,,253357000000.0,205848750000.0,0.0,1.0,-0.7071067811865476,297600000000.0,0.0,0.3107991411650898,26.079451087822903
MSFT,2024-12-31T00:00:00.000000,89035000000.0,245122000000.0,218435666666.66666,0.13400558612967717,371905000000.0,205848750000.0,0.0,1.0,-0.7071067811865476,318078500000.0,0.0,0.3023555617202862,26.225021882734282
```

### What it does (per family)
- **Temporal, per entity:** `lag(x, n)` (explicit period count), `yoy(x)` (stdlib, 1-arg), `ttm(x)` (kind-aware: for a `flow` field = trailing 4-period sum; on an **annual** panel that is the value itself → no-op), `roll_mean(x, n)` (trailing n-period mean), `cagr(x, n)` (stdlib macro; `roll_*` windows behave analogously), `cumsum`, `ts_mean` (whole-series mean per entity), `drawdown` (x/cummax(x) − 1).
- **Cross-sectional, per period:** `rank` (AAPL>MSFT revenue → rank 2.0/1.0 here; 2 entities), `zscore` (±0.707 with 2 entities), `xs_mean`, `pctile`.
- **Elementwise / null semantics:** `/` desugars to `safe_div` (0/0 or x/0 → null); `log`; `??`/`coalesce`/`fill_null`/`is_null` (see §6).
- Nulls at window edges are normal: `cfo_lag2` empty for 2020/2021 (needs 2 prior periods); `rev_cagr3` empty until 3 prior periods exist.

### Gotchas
- **`lag` requires an explicit period count:** `lag(x)` → `E-FUNC-ARITY` ("lag takes 2..2 args, got 1"); use stdlib `yoy(x)` for the 1-arg case.
- **`export` takes ONE name per statement:** `export a, b` → `ERROR SYNTAX at line 19, column 20: unexpected ','`.
- With only 2 entities, cross-sectional functions are degenerate but still defined (rank ∈ {1,2}, zscore = ±1/√2).

---

## 5. PIT / as-of / filing-date semantics

### Goal
Show how period keys, filing dates, and `pit: auto` vs `pit: naive` shape the panel; where restatements would surface.

### Command (verbatim) — quarterly frame via the frequency prefix
```
# qtr2.trail (full text)
# Real 10-Q quarterly data: the FREQUENCY PREFIX on the field selects the fetch frequency.
model qtr2 at quarterly {
    export rev = quarterly.edgar.revenue
}
$ .venv/bin/trail run qtr2.trail --model qtr2 --config trail.yaml --out qtr2.csv
```

### Real output
```
WARN  W-PIT-PARTIAL 9 row(s) carry no '__date:filing_date' coordinate; placing those at period-end (naive)
wrote qtr2.csv
```
`qtr2.csv` — 29 data rows. Verbatim head/tail (MSFT 12-31 rows show the fiscal-Q4 label quirk):
```
entity,time,rev
AAPL,2020-12-31T00:00:00.000000,64698000000.0
AAPL,2021-03-31T00:00:00.000000,111439000000.0
AAPL,2021-06-30T00:00:00.000000,89584000000.0
AAPL,2021-09-30T00:00:00.000000,81434000000.0
AAPL,2021-12-31T00:00:00.000000,83360000000.0
...
MSFT,2021-03-31T00:00:00.000000,43076000000.0
MSFT,2021-06-30T00:00:00.000000,41706000000.0
MSFT,2021-12-31T00:00:00.000000,91469000000.0
MSFT,2022-03-31T00:00:00.000000,51728000000.0
MSFT,2022-06-30T00:00:00.000000,49360000000.0
...
MSFT,2024-12-31T00:00:00.000000,64727000000.0
```

### Verified mapping (source + probes, verbatim where cited)
- **Period keys** (`trail_edgar/convert.py`):
  ```python
  _Q_END = {0: (12, 31), 1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
  ```
  with the comment: *"Fiscal quarters are mapped to calendar quarter-ends of the label year - the same simplification the annual path applies (FY -> Dec 31); canonical fiscal alignment is a later phase."*
- **Raw edgartools labels** (probe `Company("MSFT").income_statement(periods=24, period="quarterly", as_dataframe=True)`): columns `Q1 2021 … Q4 2026` (24 most recent quarters); `Total Revenue` row values 37.154B (Q1 2021) … 90.007B (Q4 2026). Every panel value traces to one of these.
- **Filing-date coordinates:** direct driver load (`src.load(LoadRequest(...))`) shows the raw panel carries `__date:filing_date` per period (e.g. AAPL 2021-03-31 row ← filed 2021-01-28) — **null for every fiscal-Q4/annual row** (the 9 W-PIT-PARTIAL rows). `pit: auto` keeps those rows but places them at period-end (the warning above); `pit: naive` places everything at period-end.
- **`pit: auto` vs `pit: naive` on the same model** (verbatim):
  ```
  $ trail run qtr2.trail --model qtr2 --config trail-naive.yaml --out qtr2-naive.csv   # pit: naive
  wrote qtr2-naive.csv          # 32 data rows
  $ trail run qtr2.trail --model qtr2 --config trail.yaml --out qtr2b.csv             # pit: auto
  WARN  W-PIT-PARTIAL 9 row(s) carry no '__date:filing_date' coordinate; placing those at period-end (naive)
  wrote qtr2b.csv               # 29 data rows
  ```
  The align engine (`load_panel_for` in trail-lang, the CLI path) **retimes/merges rows vs the raw driver panel**: in the CLI `pit: auto` output, MSFT's fiscal-Q4 values land on 12-31 keys and some quarters merge (e.g. `MSFT,2021-12-31 = 91469000000` = Q4 2021 46.152B + Q1 2022 45.317B), while the raw driver panel has them as separate `(2021,4)=46.152B @ 2021-12-31` and `(2022,1)=45.317B @ 2022-03-31`. Treat the raw-driver probe as the ground truth for "what EDGAR says" and the CLI panel as the engine's aligned view.
- **`@` is a SOURCE pin, not an entity pin:** `edgar.revenue @ edgar` is the valid form (verified: `pin2.trail` with `export pinned_rev = edgar.revenue @ edgar` runs clean); `@ MSFT` (entity pin) is not supported. Align overrides like `@ truncate(filing_date, "1mo")` are rejected: `ERROR SYNTAX at line 2, column 60: unexpected ','`.

### What it does
PIT semantics = as-of filing date, restatement-aware in design: each statement row carries its 10-K/10-Q filing date (`__date:filing_date`), and `pit: auto` aligns on that coordinate. Where a coordinate is missing (fiscal Q4/annual rows here), the row is placed at period-end and flagged `W-PIT-PARTIAL`.

### Gotchas
- Fiscal-calendar simplification: fiscal Q4 is keyed Dec-31 of the label year regardless of the actual fiscal year-end month (Sept for AAPL, June for MSFT). Values are real; the *dates* are the simplification.
- The driver fetches the N most-recent quarters, so the oldest rows leave the window as fetch dates advance: MSFT's 2020-12-31 row (37.154B, raw "Q1 2021") was present in the 2026-10-25 run and absent in the 2026-10-31 re-run (29 vs 30 rows) — the quarterly analogue of §2's MSFT-2020 annual gap.
- Row counts differ between `pit: auto` and `pit: naive` — do not "fix" this; it is the PIT placement behavior.
- Restatements: no restated (duplicate-filing) period exists for AAPL/MSFT in the 2020–2024 demo window (exactly one filing-date coordinate per (ticker, period)), so restatement-aware selection cannot be demonstrated with real data here — see "Not runnable here".

---

## 6. Null semantics

### Goal
`??` coalesce and the panel's row-level null behavior.

### Model — `nulls.trail` (full text)
```
# Null semantics: ?? (coalesce) on structurally-absent lines.
model nulls at annual {
    raw_issued   = edgar.stock_issued
    issued_fill  = edgar.stock_issued ?? 0
    raw_minority = edgar.minority_interest
    minority_fill = edgar.minority_interest ?? 0
    export raw_issued
    export issued_fill
    export raw_minority
    export minority_fill
}
```

### Command + real output (complete — 6 rows)
```
$ trail run nulls.trail --model nulls --config trail.yaml --out nulls.csv
wrote nulls.csv
```
```
entity,time,raw_issued,issued_fill,raw_minority,minority_fill
AAPL,2020-12-31T00:00:00.000000,880000000.0,880000000.0,,0.0
AAPL,2021-12-31T00:00:00.000000,1105000000.0,1105000000.0,,0.0
MSFT,2021-12-31T00:00:00.000000,1693000000.0,1693000000.0,,0.0
MSFT,2022-12-31T00:00:00.000000,1841000000.0,1841000000.0,,0.0
MSFT,2023-12-31T00:00:00.000000,1866000000.0,1866000000.0,,0.0
MSFT,2024-12-31T00:00:00.000000,2002000000.0,2002000000.0,,0.0
```

### What it does
- `x ?? y` = coalesce: first non-null. `edgar.minority_interest` is structurally absent for both tickers (empty in EDGAR) → `raw_minority` empty, `minority_fill` = 0.0.
- **The panel drops (entity, period) rows where ALL loaded fields are null.** This model loads only `stock_issued`/`minority_interest`; AAPL has `stock_issued` only for FY2020/2021 in the window, so AAPL 2022–2024 rows disappear entirely (compare with `first.csv`, where AAPL has 5 rows because `revenue` is loaded). This is intended semantics — verify it, don't debug it.

### Gotchas
- Fields like `edgar.stock_issued` are "often null for buyback-heavy issuers" (driver note) — models on mostly-null fields silently lose entity-years.
- Null-safe division: `edgar.cogs / edgar.revenue` desugars to `safe_div` (0/0 or x/0 → null) — no divide-by-zero errors in `cogs_pct` above.

---

## 7. Config

### Goal
Document every knob exercised, with effect.

### Config (variants created in the work dir)
| Config | Diff from `trail.yaml` | Verified effect |
|---|---|---|
| `trail.yaml` | — | baseline: `pit: auto` |
| `trail-naive.yaml` | `panel.pit: naive` | quarterly run: no `W-PIT-PARTIAL` warning; 32 rows vs 29 |
| `trail-noid.yaml` | no `identity` option; `EDGAR_IDENTITY` unset | coded error (see §9) |
| `trail-badtkr.yaml` | `tickers: [ZZZZZZZ]` | raw traceback `CompanyNotFoundError` (see §9) |
| `trail-oldyears.yaml` | `panel.periods: [1900, 1910]` | empty frame, no error (see §9) |
| `trail-coldcache.yaml` | fresh `cache_dir` | used for cold/warm timing (§8) |

### CLI/config interaction (verbatim)
```
$ trail validate --config trail.yaml
Usage: trail validate [OPTIONS] PATH
Try 'trail validate --help' for help.
Error: No such option '--config'.        # validate has no config flag; run does
```
Config keys used: `sources.<name>.driver` (`edgar`), `sources.<name>.options.{identity,tickers,years,cache_dir}`, `precedence.default` (list of source names), `panel.{periods,pit,strict}`.

### Gotchas
- `years` (source option) drives how many most-recent fiscal periods the driver fetches; `panel.periods` is the requested panel window. They can diverge (see MSFT FY2020 gap, §2).
- Identity resolution: `options.identity` first, then `EDGAR_IDENTITY` env; without either → coded error.

---

## 8. Caching

### Goal
Show the cache and its effect.

### Command (verbatim)
```
sed 's|cache_dir: .edgar-cache|cache_dir: .edgar-cache-cold|' trail.yaml > trail-coldcache.yaml
time .venv/bin/trail run first.trail --model rev_frame --config trail-coldcache.yaml --out first-cold.csv
time .venv/bin/trail run first.trail --model rev_frame --config trail-coldcache.yaml --out first-warm.csv
```

### Real output
```
wrote first-cold.csv
real  0m2.027s
wrote first-warm.csv
real  0m1.571s
$ du -sh .edgar-cache-cold
664K  .edgar-cache-cold
$ ls .edgar-cache-cold/_tcache
data.sec.gov
```

### What it does
`cache_dir` holds a polars `_tcache` (pickled frames keyed per source host, here `data.sec.gov`). A fresh `cache_dir` forces a refetch (cold); the second run reuses it (warm). The 664K cache is the two tickers' XBRL facts.

### Gotchas
- To demonstrate cold vs warm without deleting anything, use a **fresh** `cache_dir` value (as above); never force-delete the venv or an existing cache.
- The engine's own HTTP layer (edgartools' `httpxthrottlecache`) also caches in-process, so "cold" timing here includes whatever that layer still has warm.

---

## 9. Error handling (all verbatim)

### Missing identity (no `options.identity`, `EDGAR_IDENTITY` unset)
```
$ env -u EDGAR_IDENTITY trail run first.trail --model rev_frame --config trail-noid.yaml
ERROR CONFIG E-EDGAR-IDENTITY SEC fair-access requires an identity; set options.identity ('Your Name your.email@example.com') or EDGAR_IDENTITY
```

### Unknown ticker
```
$ trail run first.trail --model rev_frame --config trail-badtkr.yaml
Traceback (most recent call last):
  ...
    raise CompanyNotFoundError(
    ...<2 lines>...
    )
edgar.exceptions.CompanyNotFoundError: Company not found: 'ZZZZZZZ'
  Tip: Search by name with find_company("...") or pass a CIK directly.
```
(Uncoded raw traceback — the driver does not wrap this into a coded error.)

### Unknown field
```
$ trail run bad_field.trail --model bad --config trail.yaml      # model: { export x = edgar.bogus_field }
ERROR E-FIELD-UNKNOWN unknown field 'edgar.bogus_field'
```

### Syntax error
```
$ trail run bad_syntax.trail --model bad --config trail.yaml     # file: `model bad at annual { export x =`
ERROR SYNTAX at line 1, column 32
```

### Empty year range (1900–1910)
```
$ trail run first.trail --model rev_frame --config trail-oldyears.yaml
shape: (0, 3)
┌────────┬───────────────┬─────┐
│ entity ┆ time          ┆ rev │
...
└────────┴───────────────┴─────┘        # 0 rows, no error
```

### Warnings (not errors)
```
WARN  W-PIT-PARTIAL 9 row(s) carry no '__date:filing_date' coordinate; placing those at period-end (naive)
```

### What it does / gotchas
Coded errors (`ERROR <code> <message>`) cover config, schema, and parse problems; unknown tickers surface as the raw edgartools exception; empty windows produce a well-typed empty frame rather than an error.

---

## 10. MCP server interface

### Goal
Prove `trail mcp` (streamable-HTTP) is reachable and its tools work via an `mcp`-SDK client.

### Command (verbatim)
```
# server (background)
.venv/bin/trail mcp --transport streamable-http --host 127.0.0.1 --port 8123
# → banner:
MCP server (streamable-http) at http://127.0.0.1:8123/mcp
```

### The `mcp` SDK pin (verified failure + fix)
With the default-resolved `mcp` SDK 2.x, the server starts but logs:
```
mcp dep missing (FastMCP import failed: cannot import name 'FastMCP' from 'mcp.server.fastmcp' ...)
```
Root cause: `trail/mcp/server.py` does `from mcp.server.fastmcp import FastMCP`, and the SDK 2.x renamed `FastMCP` → `MCPServer`. Fix (verified):
```
.venv/bin/python -m pip install 'mcp>=1.2,<2'     # → mcp 1.30.0
```
Client-side (mcp 1.x): the helper is **`streamablehttp_client`** (no underscore), modern signature takes a **plain str URL** (the `("url",)` tuple form errors/deprecates), and it yields **three** values:
```python
async with streamablehttp_client("http://127.0.0.1:8123/mcp") as (r, w, _):
    async with ClientSession(r, w) as s:
        await s.initialize()
        await s.call_tool("schema", {"namespace": "edgar"})
```

### Verified tools (client probe, real output)
- **Tool list (10):** `functions, schema, validate, describe, eval, run, fetch, drop, views, refresh`.
- **`schema`** (`{"namespace": "edgar"}`) → the edgar field vocabulary (40 fields with kinds).
- **`fetch`** (`{"expressions": ["edgar.revenue", "edgar.cogs"], "data": {"config": "trail.yaml"}, "entities": ["AAPL"]}`) → AAPL revenue+cogs 2020–2024. **Entity pushdown works** (only AAPL rows returned).
- **`run`** (`{"name": "fundamentals", "path": "fundamentals.trail", "data": {"config": "trail.yaml"}, "entities": ["AAPL"], "to_file": "mcp-run.csv"}`) → wrote `mcp-run.csv`, shape `[5, 6]` (AAPL-only scope).
- **`eval`** (`{"expression": "yoy(edgar.revenue)", "data": {"config": "…/trail.yaml"}, "entities": ["MSFT"], "format": "compact", "limit": 5}`) → MSFT revenue YoY, matching the CLI output. `{"expression": "lag(edgar.revenue)"}` → the same `E-FUNC-ARITY` as the CLI (consistency check).
- **`validate`** (`{"source": "model m at annual { export x = edgar.revenue }", "data": {"config": "…/trail.yaml"}}`) → valid, no issues.

### Gotchas
- SDK pin is load-bearing (`mcp>=1.2,<2`); with `mcp>=2` the server exposes **no tools**.
- `data` is passed as `{"config": "<path>"}` — the MCP config-data shape.
- The stdio transport is the default; use `--transport streamable-http --host … --port …` for HTTP clients.

---

## 11. CLI (all options)

### Real output — `trail --help`
```
Usage: trail [OPTIONS] COMMAND [ARGS]...

  Trail - financial expression language.

Options:
  --help  Show this message and exit.

Commands:
  catalog   Discover fields, functions, and sources.
  describe  Discover what a provider actually publishes: the available...
  mcp       Run the Trail MCP server.
  repl      Launch the interactive Trail REPL.
  run
  signal    Run a `signal` declaration: a one-export, no-score model.
  validate
  web       Launch the Trail REPL Web Console.
```
There is **no `backtest`** and **no `init`/scaffold** command (verified on PyPI 0.18.0: `Error: No such command 'backtest'`).

### Per-command (verified)
- **run** — `trail run PATH --model NAME [--config PATH] [--no-stdlib] [--out PATH]`. `--model` required.
- **signal** — `trail signal PATH --name NAME [--config PATH] [--no-stdlib] [--out PATH]` (verified via `--help`): runs a `signal` declaration (one export, no score) and prints or writes (`--out`) the resulting `[entity, time, NAME]` series.
- **validate** — `trail validate PATH [--no-stdlib]` → prints `OK`; no `--config`.
- **describe** — `trail describe model.trail` → panel shape + namespace fields + categorical distributions.
- **catalog** — four verified forms:
  ```
  $ trail catalog
  Trail catalog - 45 fields across 2 namespaces, 68 primitive + 84 derived functions, 1 source(s).
  ...
  │ edgar     ┆ 40     │
  │ meta      ┆ 5      │
  $ trail catalog edgar.revenue
  Field edgar.revenue
  │ column ┆ edgar.revenue │
  │ kind   ┆ flow          │
  $ trail catalog sources
  Sources (1) | precedence: default=[edgar]
  │ edgar ┆ edgar │
  $ trail catalog cagr
  Function cagr
  │ layer ┆ derived │
  │ args  ┆ 2       │
  │ kind  ┆ stdlib macro │
  ```
- **mcp** — see §10.
- **repl** — fixed on trail-lang main (PR #55, merged 2026-10-31); **not in the PyPI 0.18.0 wheel** — see the note at the start of §12. **web** — broken on 0.18.0; see §12.

---

## 12. REPL (fixed in trail-lang PR #55)

### Verified baseline

- **trail-lang git main @ `52958d8`** — the REPL fix (PR #55, merged 2026-10-31) is on main but is **not in the PyPI 0.18.0 wheel**. Start from the §1 venv (fresh `.venv` from PyPI: `trail-lang` + `trail-edgar` + `prompt_toolkit`) and upgrade `trail-lang` to git main:
  ```
  .venv/bin/pip install 'git+https://github.com/trail-language/trail-lang.git'
  ```
  (verified 2026-10-31 in a fresh venv: installs trail-lang 0.18.0 from git main; `import trail.repl.loop` — the module the PyPI 0.18.0 wheel cannot import — succeeds.)
- CPython 3.13.13; same work dir and `trail.yaml` as §1–§11.
- Verified 2026-10-31 (full pty transcripts + lead re-check); all outputs below verbatim from the pty captures (ANSI stripped).

**prompt_toolkit 3.x caveat:** piped stdin is refused (`Warning: Input is not a terminal (fd=0)`, then clean exit after the banner) — a prompt_toolkit limitation, not a trail bug. The sessions below were driven through a pty — on Unix: `script -qec "trail repl --config trail.yaml" /dev/null < lines.txt` — but `script` is **unix-only** (not on Windows). The platform-neutral driver is the in-process `ReplSession` API — the exact code path the loop calls (`run_repl` → `session.process_input` per line):
```python
from trail.config import load_config
from trail.repl.session import ReplSession

s = ReplSession(config=load_config("trail.yaml"))  # without a config the bundled fixture panel loads, but its fields are not schema-registered - see Known limitations
r = s.process_input("edgar.revenue")               # -> Result; r.value is the polars frame
```

### Startup + catalog

`trail repl --config trail.yaml` — banner (version now derived from the installed package, not a stale hardcode), then `?` — the catalog for the active config (edgar 40 / meta 5):

```
  Trail REPL v0.18.0
  Expression language for financial indicators.
  Try: income.revenue / balance.total_assets
  Or:  margin = income.operating_income / income.revenue
  Help:  ?  ?fields  ?functions  ?sources  ?income
  Quit:  Ctrl-D or Ctrl-C twice
trail> ?
  (2 rows × 2 cols)
shape: (2, 2)
┌───────────┬────────┐
│ namespace ┆ fields │
│ ---       ┆ ---    │
│ str       ┆ i64    │
╞═══════════╪════════╡
│ edgar     ┆ 40     │
│ meta      ┆ 5      │
└───────────┴────────┘
```

### Bare field on real data

```
trail> edgar.revenue
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 2.7452e11     │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 3.6582e11     │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 3.9433e11     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 3.8328e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 3.9104e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 1.6809e11     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 1.9827e11     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 2.1192e11     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 2.4512e11     │
└────────┴─────────────────────┴───────────────┘
```

The 9-row frame is identical to `first.csv` (§2) — the session is config-backed (real SEC data), not the bundled fixture panel.

### Assignment

```
trail> rev = edgar.revenue
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────┐
│ entity ┆ time                ┆ rev       │
│ ---    ┆ ---                 ┆ ---       │
│ str    ┆ datetime[μs]        ┆ f64       │
╞════════╪═════════════════════╪═══════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 2.7452e11 │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 3.6582e11 │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 3.9433e11 │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 3.8328e11 │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 3.9104e11 │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 1.6809e11 │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 1.9827e11 │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 2.1192e11 │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 2.4512e11 │
└────────┴─────────────────────┴───────────┘
```

### `def` + call (user function on real data)

```
trail> def dbl(x) = x * 2
  (no output)
trail> dbl(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 5.4903e11     │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 7.3163e11     │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 7.8866e11     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 7.6657e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 7.8207e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 3.3618e11     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 3.9654e11     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 4.2383e11     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 4.9024e11     │
└────────┴─────────────────────┴───────────────┘
```

### Universe decl + model binding (7-row screen)

```
trail> universe big = stocks where edgar.revenue > 200000000000
  (no output)
trail> model m on big { export r = edgar.revenue }
  (7 rows × 3 cols)
shape: (7, 3)
┌────────┬─────────────────────┬───────────┐
│ entity ┆ time                ┆ r         │
│ ---    ┆ ---                 ┆ ---       │
│ str    ┆ datetime[μs]        ┆ f64       │
╞════════╪═════════════════════╪═══════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 2.7452e11 │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 3.6582e11 │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 3.9433e11 │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 3.8328e11 │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 3.9104e11 │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 2.1192e11 │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 2.4512e11 │
└────────┴─────────────────────┴───────────┘
```

All 5 AAPL rows pass the $200B screen; MSFT keeps only 2023/2024 (2021/2022 < $200B). The universe is stored in the session and bound by the model.

### Coded error (wrong arity → shared validator)

```
trail> lag(edgar.revenue)
  Error: E-FUNC-ARITY lag takes 2..2 args, got 1
```

### Known limitation (cosmetic)

The banner's static "Try:" hint line still shows the fixture fields (`income.revenue`, `balance.total_assets`) in a config-backed session — one-line cosmetic in `trail/repl/loop.py`; follow-up candidate for trail-lang.

- **No-config field queries fail (engine gap, not a REPL bug):** without `--config` / a local `trail.yaml`, the session runs on the bundled fixture panel, but the fixture declares no `trail.schema` entry point (each source package declares its own field vocabulary; the engine core only registers `meta.*`), so every bare field reference fails static validation with `E-FIELD-UNKNOWN` - including the fixture's own `income.*`/`balance.*`/`cash.*`/`price.*` columns. The `?` catalog still works; field queries need a config. Verified pre-existing on both PyPI 0.18.0 and trail-lang main @ 52958d8 (2026-10-31).


### `trail web` — broken (verified)
```
$ .venv/bin/trail web --host 127.0.0.1 --port 8099
Trail REPL Web Console running on http://127.0.0.1:8099
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8099/
501
```
Root cause 1: `trail/web/server.py` defines `REPLHandler._do_GET`/`_do_POST` (underscore-prefixed) with **no `do_GET`/`do_POST` aliases**, so `BaseHTTPRequestHandler` answers every request 501. Side-probe proof (monkeypatch `do_GET = _do_GET`, `do_POST = _do_POST` on a separate port): the REST API then works —
```
$ curl -s -X POST http://127.0.0.1:8098/api/sessions -H 'Content-Type: application/json' -d '{}'
{"session_id": "1bb8b504"}
$ curl -s -X POST http://127.0.0.1:8098/api/sessions/1bb8b504/execute -d '{"input":"?functions"}'
{"input": "?functions", "error": null, "type": "result", "output": {"rows": 152, "columns": ["function","layer","axis","args","summary"], "preview": [...abs, acos, asin, asof...]}}
```
Root cause 2: `_do_GET` does `path = parsed.path.rstrip("/")` then compares `path == "/"` — the root URL becomes `""`, so even with the aliases, `GET /` 404s. (The UI HTML is never served.)

---

## Environment (verified)

- **Python:** 3.13.13 (CPython; both packages declare `requires_python >= 3.11`).
- **Engine:** trail-lang **0.18.0** from PyPI for §1–§11; §12 (REPL) uses trail-lang **git main** (the post-0.18.0 REPL fix) via the one-liner in §12. (The editable-install dev workflow is Appendix A.)
- **Driver:** trail-edgar **0.5.0** from PyPI.
- **Key deps (PyPI-resolved):** edgartools 5.62.1 (import name `edgar`), polars 2.1.0, lark 1.3.1, prompt_toolkit 3.0.53 (installed manually — §1), mcp 1.30.0 after the §10 pin (the `[mcp]` extra alone resolves **mcp 2.3.0**).
- **Working dir:** one directory (e.g. `trail-work/`) holding `.venv/`, `trail.yaml`, the `.trail` models, CSVs, and `.edgar-cache/` (~664K `_tcache/data.sec.gov` after the first fetch).
- **Identity:** redacted here as `$EDGAR_IDENTITY` — the SEC fair-access `Name email` string, set via `options.identity` (§1) or the `EDGAR_IDENTITY` env var.
- **MCP server:** `.venv/bin/trail mcp --transport streamable-http --host 127.0.0.1 --port 8123` → `http://127.0.0.1:8123/mcp`.

## Not runnable here

- **Restatement-aware PIT:** no restated (re-filed) period exists for AAPL/MSFT in the 2020–2024 window (one filing-date coordinate per (ticker, period)); the mechanism (as-of = latest filing date; `W-PIT-PARTIAL` placement) is verified but cannot be demonstrated against real restated data in this window.
- **Piped-stdin `trail repl`:** prompt_toolkit 3.x refuses non-TTY stdin (`Input is not a terminal (fd=0)` → clean exit after the banner); drive the REPL through a pty (Unix) or the in-process `ReplSession` API (§12).
- **`trail repl` on the PyPI 0.18.0 wheel:** the REPL fix is on trail-lang main (merged 2026-10-31) but not in the 0.18.0 release — the git upgrade in §12 is required.
- **`trail web` UI/API:** broken on 0.18.0 (missing `do_GET`/`do_POST` aliases → 501; root-path `rstrip("/")` bug → 404). Underlying REST verified only via a monkeypatch side-probe (§12).
- **Historical as-of-date PIT queries:** the config has no "as-of date" parameter; PIT manifests as which rows are visible/placed per filing-date coordinate (`auto` vs `naive`), not a query-time date.
- **Other sources (trail-gmd, trail-fmp):** not installed; not exercised.
- **Live-marked trail-edgar tests** (`pytest -m live`): excluded by default (network-heavy); not run.

## Appendix A — developing trail-lang / trail-edgar (editable install from git)

The main flow uses PyPI. If you are developing the engine or the driver, clone both repos and install them editable instead (replaces the `pip install trail-lang trail-edgar` step in §1):

```
git clone https://github.com/trail-language/trail-lang.git
git clone https://github.com/trail-language/trail-edgar.git
.venv/bin/pip install -e "path/to/trail-lang[mcp]" -e path/to/trail-edgar
```

- The editable install picks up your local commits, so CLI/REPL behavior is that of your working tree (e.g. the REPL fix, PR #55, is on main before the 0.18.0 PyPI release).
- Extras: on main both `[mcp]` and `[repl]` (`prompt_toolkit>=3`) are declared; on PyPI 0.18.0 only `[mcp]` is.
- Upstream state at verification time: trail-edgar `main @ bdd58f3` = v0.5.0; the PyPI trail-lang 0.18.0 release includes the `signal` command.
- Test suites (read-only runs, `-p no:cacheprovider`): trail-edgar `36 passed, 1 deselected`; trail-lang (with the REPL fix) `538 passed, 1 skipped` (incl. 22 REPL tests). One pre-existing engine bug: `ewm_std` returns `None` where `tests/test_ops_factor.py` expects `0.0` (that test fails; everything else passes).
