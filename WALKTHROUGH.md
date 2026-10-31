# Trail — end-to-end walkthrough (REPL-first)

**How to use this guide:**

- **Python ≥ 3.11** (every command below runs on CPython 3.14).
- **`trail-lang 0.19.1` + `trail-edgar 0.6.0`** (both on PyPI), installed with `pipx` in §1.
- Running example throughout: **AAPL + MSFT, fiscal years 2020–2024**, SEC EDGAR via the `edgar` driver.
- You need an SEC fair-access identity string (`"Your Name your.email@example.com"`). It appears as the `$EDGAR_IDENTITY` placeholder — substitute your own value in local files and never commit it.
- **Everything is REPL-driven.** Setup is two `pipx` commands plus one `trail init` prompt; every data section below is a live REPL session. No hand-written YAML, no script files, no CSVs.
- Every output block below is a verbatim terminal capture from a fresh install of exactly these versions (identity redacted). The REPL captures were taken through a unix pty — how to reproduce that on other platforms: §10.

---

## 1. Setup (pipx)

Two commands. `trail-edgar` is a **driver library** — it provides the `edgar` source driver's entry point and has no CLI of its own — so it is **injected** into the `trail-lang` environment rather than installed as a standalone app:

```
$ pipx install trail-lang
done! ✨ 🌟 ✨
  installed package trail-lang 0.19.1, installed using Python 3.14.4
  These apps are now globally available
    - trail

$ pipx inject trail-lang trail-edgar
done! ✨ 🌟 ✨
  injected package trail-edgar into venv trail-lang
```

Verify:

```
$ trail --version
trail 0.19.1
```

That is the entire install. `prompt_toolkit` is a core dependency of `trail-lang` as of 0.19.0, so `trail repl` works out of the box — there is no extra install step.

**Why not `pipx install trail-edgar` on its own?** It's a library, not an app — pipx refuses (exit 1):

```
No apps associated with package trail-edgar. Try again with '--include-deps'
to include apps of dependent packages, which are listed above. If you are
attempting to install a library, pipx should not be used. Consider using pip
or a similar tool instead.
```

(The full output then lists the CLI apps of its dependent packages — including the `trail` app that belongs to `trail-lang` itself — before exiting.)

**Upgrading:** `pipx install --force trail-lang` upgrades in place and preserves injected packages; re-run `pipx inject trail-lang trail-edgar` afterwards to refresh the driver.

---

## 2. Config — `trail init edgar` (the only config step)

Config is produced by the driver, not written by hand. `trail init <driver>` discovers the installed driver package and prompts for that driver's options; every prompt has a sensible default, so just press Enter:

```
$ trail init edgar
trail-edgar 0.6.0 found (driver: edgar)
SEC fair-access identity ("Your Name your.email@example.com"): $EDGAR_IDENTITY
Tickers (comma-separated) [AAPL,MSFT]: 
Years (start,end) [2020,2024]: 
wrote trail.yaml
```

(Identity typed; tickers and years accept the defaults on Enter.)

It writes a commented, self-documenting `trail.yaml` (identity redacted here):

```yaml
# Minimal Trail config: SEC EDGAR source, 2-ticker universe, annual 2020-2024.
sources:
  edgar:
    driver: edgar                      # source driver name (entry point provided by trail-edgar)
    options:
      identity: "$EDGAR_IDENTITY"            # SEC fair-access 'Your Name your.email@example.com'
      tickers: [AAPL, MSFT]             # tickers to fetch
      years: [2020, 2024]                 # the N most-recent fiscal years the driver fetches
      cache_dir: .edgar-cache          # local cache dir (relative paths are fine)
precedence:
  default: [edgar]                     # field-namespace -> source resolution order
panel:
  periods: [2020, 2024]                   # requested panel window
  pit: auto                            # as-of filing-date placement
  strict: false
```

A flag form skips the prompts (for automation):

```
$ trail init edgar --identity "$EDGAR_IDENTITY" --tickers AAPL,MSFT --years 2020,2024 --output trail-flag.yaml
trail-edgar 0.6.0 found (driver: edgar)
wrote trail-flag.yaml
```

(`--force` overwrites an existing file; `--output` defaults to `trail.yaml`.)

Every section below runs `trail repl --config trail.yaml` from the directory containing this file.

---

## 3. The catalog (REPL)

Start the REPL. The banner is shown in full once here and omitted in later sessions.

```
$ trail repl --config trail.yaml
  Trail REPL v0.19.1
  Expression language for financial indicators.
  Try: income.revenue / balance.total_assets
  Or:  margin = income.operating_income / income.revenue
  Help:  ?  ?fields  ?functions  ?sources  ?income
  Quit:  Ctrl-D or Ctrl-C twice

trail> ?
  (6 rows × 2 cols)
shape: (6, 2)
┌───────────┬────────┐
│ namespace ┆ fields │
│ ---       ┆ ---    │
│ str       ┆ i64    │
╞═══════════╪════════╡
│ balance   ┆ 18     │
│ cash      ┆ 8      │
│ edgar     ┆ 40     │
│ income    ┆ 14     │
│ meta      ┆ 5      │
│ price     ┆ 2      │
└───────────┴────────┘
trail> ?sources
  (1 rows × 2 cols)
shape: (1, 2)
┌────────┬────────┐
│ source ┆ driver │
│ ---    ┆ ---    │
│ str    ┆ str    │
╞════════╪════════╡
│ edgar  ┆ edgar  │
└────────┴────────┘
trail> ? edgar
  (40 rows × 2 cols)
shape: (10, 2)
┌─────────────────────────────────┬───────┐
│ field                           ┆ kind  │
│ ---                             ┆ ---   │
│ str                             ┆ str   │
╞═════════════════════════════════╪═══════╡
│ edgar.accounts_payable          ┆ stock │
│ edgar.accounts_receivable       ┆ stock │
│ edgar.capex                     ┆ flow  │
│ edgar.cash_and_equivalents      ┆ stock │
│ edgar.cash_and_short_term_inve… ┆ stock │
│ edgar.cff                       ┆ flow  │
│ edgar.cfi                       ┆ flow  │
│ edgar.cfo                       ┆ flow  │
│ edgar.cogs                      ┆ flow  │
│ edgar.common_stock              ┆ stock │
└─────────────────────────────────┴───────┘
  ... 20 rows omitted ...
shape: (10, 2)
┌─────────────────────────────────┬───────┐
│ field                           ┆ kind  │
│ ---                             ┆ ---   │
│ str                             ┆ str   │
╞═════════════════════════════════╪═══════╡
│ edgar.retained_earnings         ┆ stock │
│ edgar.revenue                   ┆ flow  │
│ edgar.sga                       ┆ flow  │
│ edgar.stock_issued              ┆ flow  │
│ edgar.total_assets              ┆ stock │
│ edgar.total_debt                ┆ stock │
│ edgar.total_equity              ┆ stock │
│ edgar.total_liabilities         ┆ stock │
│ edgar.weighted_average_shares   ┆ stock │
│ edgar.weighted_average_shares_… ┆ stock │
└─────────────────────────────────┴───────┘
trail> ? edgar.revenue
  (2 rows × 2 cols)
shape: (2, 2)
┌──────────┬───────────────┐
│ property ┆ value         │
│ ---      ┆ ---           │
│ str      ┆ str           │
╞══════════╪═══════════════╡
│ column   ┆ edgar.revenue │
│ kind     ┆ flow          │
└──────────┴───────────────┘
```

- `?` — per-namespace field counts. The six namespaces are *advertised*; the columns actually usable in this session are the ones your driver publishes (§4) plus `meta.*`.
- `? <namespace>` — the namespace's fields (the REPL shows the first and last 10 rows; the `…` inside cells is the same truncation). `?fields` (87 rows) and `?functions` (152 rows) list the whole catalog the same way.
- `? <field>` — a single column's details (name and `kind`: `flow` vs `stock` — matters for `ttm`, §6).
- **The catalog is the source of truth for valid column names in this session** — use the names you see here (e.g. `edgar.revenue`), not the banner's `Try:` hint (see §11).

---

## 4. Core fields (REPL)

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

- **9 rows, not 10 — MSFT has no 2020 row** (AAPL 5 + MSFT 4). The driver fetches the N most-recent fiscal years (N derived from the config's `years` window), and MSFT's most-recent-6 window (FY2021–FY2026) does not reach calendar 2020, so the requested year 2020 is silently dropped from its series. Requested years outside the driver's fetch window drop **silently (no warning)** — check row counts per ticker.
- Time key = **Dec 31 of the fiscal-year label**: AAPL FY2024 (ended 2024-09-30) and MSFT FY2024 (ended 2024-06-30) are both keyed `2024-12-31`.
- `rev = edgar.revenue` is an assignment: `rev` becomes a named column you can use in later expressions.

---

## 5. Fundamentals (REPL)

```
trail> yoy(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 0.332594      │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 0.077938      │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ -0.028005     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 0.02022       │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 0.179561      │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 0.06882       │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.1567        │
└────────┴─────────────────────┴───────────────┘
trail> gross_margin(edgar.gross_profit, edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 0.382332      │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 0.417794      │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 0.433096      │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 0.441311      │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 0.462063      │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 0.689258      │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 0.684017      │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 0.689201      │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.697644      │
└────────┴─────────────────────┴───────────────┘
trail> net_margin(edgar.net_income, edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 0.209136      │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 0.258818      │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 0.253096      │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 0.253062      │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 0.239713      │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 0.364517      │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 0.366863      │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 0.341462      │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.35956       │
└────────┴─────────────────────┴───────────────┘
```

- `yoy(x)` is the stdlib one-arg YoY (it wraps `lag(x, 1)`); `gross_margin`/`net_margin` take **(numerator, denominator)**.
- First available period is `null` for each entity (no prior period to compare) — for MSFT that is 2021, the same gap as §4 showing up.

---

## 6. Functions (REPL)

One session covering the function suite — temporal, cross-sectional, math, and user-defined `def` — ending with two error demos.

```
trail> lag(edgar.cfo, 2)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 8.0674e10     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 1.0404e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 1.2215e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 7.6740e10     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 8.9035e10     │
└────────┴─────────────────────┴───────────────┘
trail> ttm(edgar.revenue)
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
trail> roll_mean(edgar.revenue, 3)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 3.4489e11     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 3.8114e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 3.8955e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 1.9276e11     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 2.1844e11     │
└────────┴─────────────────────┴───────────────┘
trail> cagr(edgar.revenue, 3)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 0.117683      │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 0.02247       │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ null          │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.134006      │
└────────┴─────────────────────┴───────────────┘
trail> cumsum(edgar.cfo)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 8.0674e10     │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 1.8471e11     │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 3.0686e11     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 4.1741e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 5.3566e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 7.6740e10     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 1.6578e11     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 2.5336e11     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 3.7190e11     │
└────────┴─────────────────────┴───────────────┘
trail> ts_mean(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 3.6180e11     │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 3.6180e11     │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 3.6180e11     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 3.6180e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 3.6180e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 2.0585e11     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 2.0585e11     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 2.0585e11     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 2.0585e11     │
└────────┴─────────────────────┴───────────────┘
trail> drawdown(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 0.0           │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 0.0           │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 0.0           │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ -0.028005     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ -0.008351     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 0.0           │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 0.0           │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 0.0           │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.0           │
└────────┴─────────────────────┴───────────────┘
trail> rank(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 1.0           │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 2.0           │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 2.0           │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 2.0           │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 2.0           │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 1.0           │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 1.0           │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 1.0           │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 1.0           │
└────────┴─────────────────────┴───────────────┘
trail> zscore(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 0.707107      │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 0.707107      │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 0.707107      │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 0.707107      │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ -0.707107     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ -0.707107     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ -0.707107     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ -0.707107     │
└────────┴─────────────────────┴───────────────┘
trail> xs_mean(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 2.7452e11     │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 2.6695e11     │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 2.9630e11     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 2.9760e11     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 3.1808e11     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 2.6695e11     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 2.9630e11     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 2.9760e11     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 3.1808e11     │
└────────┴─────────────────────┴───────────────┘
trail> pctile(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ null          │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 1.0           │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 1.0           │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 1.0           │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 1.0           │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 0.0           │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 0.0           │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 0.0           │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.0           │
└────────┴─────────────────────┴───────────────┘
trail> edgar.cogs / edgar.revenue
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 0.617668      │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 0.582206      │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 0.566904      │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 0.558689      │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 0.537937      │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 0.310742      │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 0.315983      │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 0.310799      │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 0.302356      │
└────────┴─────────────────────┴───────────────┘
trail> log(edgar.revenue)
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────────────┐
│ entity ┆ time                ┆ __repl_result │
│ ---    ┆ ---                 ┆ ---           │
│ str    ┆ datetime[μs]        ┆ f64           │
╞════════╪═════════════════════╪═══════════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 26.338272     │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 26.625399     │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 26.700449     │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ 26.672045     │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ 26.692063     │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 25.847753     │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 26.012896     │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 26.079451     │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 26.225022     │
└────────┴─────────────────────┴───────────────┘
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
trail> lag(edgar.revenue)
  Error: E-FUNC-ARITY lag takes 2..2 args, got 1
trail> edgar.bogus_field
  Error: E-FIELD-UNKNOWN unknown field 'edgar.bogus_field'
```

- **Temporal, per entity:** `lag(x, n)` (explicit period count), `ttm(x)` (kind-aware: for a `flow` field = trailing 4-period sum; on an **annual** panel that is the value itself → no-op, as captured), `roll_mean(x, n)` (trailing n-period mean), `cagr(x, n)`, `cumsum(x)`, `ts_mean(x)` (whole-series mean per entity), `drawdown(x)` (= x/cummax(x) − 1).
- **Cross-sectional, per period:** `rank` (AAPL > MSFT on revenue here → 2.0/1.0), `zscore` (±0.707107 = ±1/√2 with 2 entities; `null` in periods where only 1 entity exists — 2020), `xs_mean`, `pctile`. With only 2 entities these are degenerate but still defined.
- **Nulls at window edges are normal:** `lag(x, 2)` is null until 2 prior periods exist; `cagr(x, 3)` until 3 do.
- **User functions:** `def dbl(x) = x * 2` (prints no output) defines `dbl`, callable on any column like a builtin.
- **Errors are coded, one-line, and non-fatal:** `E-FUNC-ARITY` (lag requires an explicit period count — use stdlib `yoy(x)` for the 1-arg case), `E-FIELD-UNKNOWN` (typo, or a column not in this session's catalog). The REPL keeps running.

---

## 7. Quarterly + point-in-time (REPL)

```
trail> model qtr2 at quarterly { export rev = quarterly.edgar.revenue }
WARN  W-PIT-PARTIAL 9 row(s) carry no '__date:filing_date' coordinate; placing those at period-end (naive)
  (29 rows × 3 cols)
shape: (10, 3)
┌────────┬─────────────────────┬───────────┐
│ entity ┆ time                ┆ rev       │
│ ---    ┆ ---                 ┆ ---       │
│ str    ┆ datetime[μs]        ┆ f64       │
╞════════╪═════════════════════╪═══════════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ 6.4698e10 │
│ AAPL   ┆ 2021-03-31 00:00:00 ┆ 1.1144e11 │
│ AAPL   ┆ 2021-06-30 00:00:00 ┆ 8.9584e10 │
│ AAPL   ┆ 2021-09-30 00:00:00 ┆ 8.1434e10 │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ 8.3360e10 │
│ AAPL   ┆ 2022-03-31 00:00:00 ┆ 1.2394e11 │
│ AAPL   ┆ 2022-06-30 00:00:00 ┆ 9.7278e10 │
│ AAPL   ┆ 2022-09-30 00:00:00 ┆ 8.2959e10 │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ 9.0146e10 │
│ AAPL   ┆ 2023-03-31 00:00:00 ┆ 1.1715e11 │
└────────┴─────────────────────┴───────────┘
  ... 9 rows omitted ...
shape: (10, 3)
┌────────┬─────────────────────┬───────────┐
│ entity ┆ time                ┆ rev       │
│ ---    ┆ ---                 ┆ ---       │
│ str    ┆ datetime[μs]        ┆ f64       │
╞════════╪═════════════════════╪═══════════╡
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ 9.1469e10 │
│ MSFT   ┆ 2022-03-31 00:00:00 ┆ 5.1728e10 │
│ MSFT   ┆ 2022-06-30 00:00:00 ┆ 4.9360e10 │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ 1.0199e11 │
│ MSFT   ┆ 2023-03-31 00:00:00 ┆ 5.2747e10 │
│ MSFT   ┆ 2023-06-30 00:00:00 ┆ 5.2857e10 │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ 1.1271e11 │
│ MSFT   ┆ 2024-03-31 00:00:00 ┆ 6.2020e10 │
│ MSFT   ┆ 2024-06-30 00:00:00 ┆ 6.1858e10 │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ 6.4727e10 │
└────────┴─────────────────────┴───────────┘
```

- **Row count is 29 (AAPL 17 + MSFT 12), not tickers × years × 4.** The driver fetches the N most-recent quarters (rolling), so the quarterly window slides as new quarters are published and the oldest rows can leave it — the quarterly analogue of §4's gap (MSFT's series starts a year later, at 2021-03-31). Quarters EDGAR didn't publish for the window are simply absent (see the MSFT tail: 2022-09-30, 2023-09-30, and 2024-09-30 are missing).
- **PIT (as-of filing date) placement:** the config's `pit: auto` places each row as of its 10-K/10-Q filing date. The `WARN` says 9 rows (the fiscal-Q4/annual rows) carry no filing-date coordinate and are placed at period-end (naive) instead. The same model under `pit: naive` (everything at period-end) returns **32 rows** — do not "fix" the discrepancy; it is the PIT placement behavior.
- The model is written as a **single-line brace block** — see §11 on multi-line input.

---

## 8. Universes, models, signals (REPL)

```
trail> signal s = edgar.revenue > 200000000000
  (9 rows × 3 cols)
shape: (9, 3)
┌────────┬─────────────────────┬───────┐
│ entity ┆ time                ┆ s     │
│ ---    ┆ ---                 ┆ ---   │
│ str    ┆ datetime[μs]        ┆ bool  │
╞════════╪═════════════════════╪═══════╡
│ AAPL   ┆ 2020-12-31 00:00:00 ┆ true  │
│ AAPL   ┆ 2021-12-31 00:00:00 ┆ true  │
│ AAPL   ┆ 2022-12-31 00:00:00 ┆ true  │
│ AAPL   ┆ 2023-12-31 00:00:00 ┆ true  │
│ AAPL   ┆ 2024-12-31 00:00:00 ┆ true  │
│ MSFT   ┆ 2021-12-31 00:00:00 ┆ false │
│ MSFT   ┆ 2022-12-31 00:00:00 ┆ false │
│ MSFT   ┆ 2023-12-31 00:00:00 ┆ true  │
│ MSFT   ┆ 2024-12-31 00:00:00 ┆ true  │
└────────┴─────────────────────┴───────┘
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

- `signal <name> = <expr>` — a one-export, no-score model: a boolean series over the full panel (9 rows).
- `universe <name> = stocks where <predicate>` — a named filter over the panel (prints no output). `model <name> on <universe> { export ... }` runs an export on it: 7 rows here (AAPL all 5 years above the $200B threshold; MSFT only 2023–2024).
- **Scope:** a `signal` declared after a `universe` evaluates inside that universe (captured: the same signal returns the universe's 7 rows after `universe big`, versus the full panel's 9 rows in a fresh session). Declare it before the universe if you want the full panel.

---

## 9. Non-REPL steps (each explicitly flagged)

Everything above is the REPL. The remaining verifiable behaviors cannot be exercised from inside it; each is flagged with why.

### 9.1 Cold-cache timing — *flag: needs the shell's `time` and a second cache dir; not measurable from inside the REPL*

Two one-line files (the only files this walkthrough uses besides `trail.yaml`). `first.trail`:

```
model rev_frame at annual {
    export rev = edgar.revenue
}
```

and `trail-coldcache.yaml` — a copy of `trail.yaml` differing only in `cache_dir: .edgar-cache-cold`, so the cold run never touches the warm cache from §3–§8.

```
$ time trail run first.trail --model rev_frame --config trail-coldcache.yaml
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
real    0m4.315s
user    0m2.504s
sys     0m0.264s

$ time trail run first.trail --model rev_frame --config trail-coldcache.yaml   # second run
real    0m1.681s
user    0m2.492s
sys     0m0.259s

$ du -sh .edgar-cache-cold
672K    .edgar-cache-cold
```

The first run fetches from `data.sec.gov`; the second is fully local. (Absolute times vary with your network — the cold/warm gap is the point.)

### 9.2 Config-error cases — *flag: config validation happens at `trail run`/`trail repl` startup, before the REPL prompt appears*

**Missing identity** — a clean coded error (exit 1):

```
$ trail run first.trail --model rev_frame --config trail-noid.yaml
ERROR CONFIG E-EDGAR-IDENTITY SEC fair-access requires an identity; set options.identity ('Your Name your.email@example.com') or EDGAR_IDENTITY
```

(`trail-noid.yaml` = the generated config with the `identity:` line removed. The error also names the `EDGAR_IDENTITY` environment-variable fallback.)

**Unknown ticker** — surfaces as a raw traceback (unhandled `CompanyNotFoundError`; a known rough edge), ending in:

```
edgar.exceptions.CompanyNotFoundError: Company not found: 'ZZZZZZZ'
  Tip: Search by name with find_company("...") or pass a CIK directly.
```

### 9.3 MCP server — *flag: a protocol server, driven from a client script, not the REPL*

Without the optional SDK (exit 1):

```
$ trail mcp
ERROR the MCP server needs the optional 'mcp' dependency: pip install trail-lang[mcp]
```

**The install to use.** The `trail-lang[mcp]` extra is capped at `mcp<2` (fresh resolves land on mcp 1.x), so the verified install into the pipx environment is the straightforward one:

```
$ pipx inject trail-lang 'mcp>=1.2,<2'
installing mcp from spec 'mcp<2,>=1.2'...
done! ✨ 🌟 ✨
  injected package mcp into venv trail-lang
```

(mcp 1.30.0.) Injecting the extra itself — `pipx inject trail-lang 'trail-lang[mcp]'` — is a no-op: under PEP 610 the already-installed `trail-lang` satisfies the requirement, so pip ignores the extra and `mcp` would never land.

Start the server (the default transport is `stdio` for local MCP clients; `streamable-http` for the network):

```
$ trail mcp --transport streamable-http --host 127.0.0.1 --port 8123
INFO:     Started server process [pid]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8123 (Press CTRL+C to quit)
```

(log trimmed: a few `StreamableHTTP session manager` INFO lines in between; `[pid]` redacted.)

Then, from a second terminal. The client needs only the `mcp` SDK (not trail) — in a small venv:

```
$ python3 -m venv .mcp-client
$ .mcp-client/bin/pip install 'mcp>=1.2,<2'
```

Save this as `mcp-probe.py`:

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://127.0.0.1:8123/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await session.call_tool("schema", {"namespace": "edgar"})
            print("schema isError:", result.isError)
            print(result.content[0].text[:400])

asyncio.run(main())
```

```
$ .mcp-client/bin/python mcp-probe.py
tools: ['functions', 'schema', 'validate', 'describe', 'eval', 'run', 'fetch', 'drop', 'views', 'refresh']
schema isError: False
{
  "fields": [
    {
      "field": "edgar.accounts_payable",
      "kind": "stock"
    },
    {
      "field": "edgar.accounts_receivable",
      "kind": "stock"
    },
    {
      "field": "edgar.capex",
      "kind": "flow"
    },
    ...
```

(output trimmed at 400 characters, as the script prints.)

Ten tools; `schema` returns the namespace's field catalog as JSON.

---

## 10. Cross-platform & no-TTY

**The pty caveat.** The REPL captures in this doc were taken by driving the REPL through a unix pty (`script(1)`) — that is how you script an interactive prompt. `script` is a unix utility (Linux `util-linux`; BSD variants on macOS have different flags) and does not exist on Windows. The transcripts are what a real terminal shows: run the same commands in a real terminal on any platform and you get the same output. The pty pipe is only how *these captures* were taken.

**Platform-neutral, no-TTY equivalent.** The REPL's engine is a plain class — usable from any script on any platform, no terminal required. Run it with the Python inside the `trail-lang` environment (for a pipx install, that interpreter lives under the venvs root printed by `pipx environment`):

```
$ vroot=$(pipx environment | sed -n 's/^PIPX_LOCAL_VENVS=//p' | tail -1)
$ "$vroot/trail-lang/bin/python" - <<'EOF'
from trail.config import load_config
from trail.repl.session import ReplSession

session = ReplSession(config=load_config("trail.yaml"))
result = session.process_input("edgar.revenue")
print(result.is_result, result.is_error)
print(result.value)
EOF
True False
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

`process_input` accepts the same statements as the REPL (`?` commands, assignments, models, …) and returns `Result(is_result, is_error, value)` — `value` is the rendered frame, the same string the terminal prints.

**`trail.yaml` is optional.** `trail repl` without `--config` validates against a built-in fixture panel instead of erroring: `income.revenue` returns a 48-row synthetic frame (tickers `AAA`–`FFF`, 2017–2024). All sessions in this doc use the config-backed edgar panel.

---

## 11. Known limitations & not runnable here

- **The banner's `Try:` hint — use `edgar.revenue`, not `income.revenue`.** The banner advertises `income.revenue`, but a config-backed edgar panel exposes only `edgar.*` (40) + `meta.*` (5) columns. The catalog still advertises all six namespaces (`income` has 14 fields), so `income.revenue` passes validation and fails at the data layer. On 0.19.1 the error renders cleanly and the REPL keeps running:

  ```
  trail> income.revenue
    Error: unable to find column "income.revenue"; valid columns: ["entity", "time", "edgar.accounts_payable", ...]
  ```

  (column list trimmed.) Use the column names from `?` / `? edgar` instead.
- **Statements are single-line.** The REPL submits each line as a complete statement; entering a multi-line model yields a per-line `PARSE ERROR` (`Unexpected token Token('$END', '')`). Keep models/universes/signals on one line, as in §7/§8.
- **Piped stdin is rejected** — the REPL requires a TTY (prompt_toolkit). For non-interactive use, use the `ReplSession` API (§10) or `trail run`.
- **`trail web` is not runnable** — on 0.19.1, `GET /` and `POST /api/sessions` both return 501 (`Unsupported method ('GET')` / `('POST')`).
- **Out of scope** — other source drivers (funda/marketdata) are not covered by this walkthrough (edgar only); tests marked live/CI-only are excluded from offline verification.

---

*`trail-lang 0.19.1` · `trail-edgar 0.6.0` · `mcp 1.30.0` (pinned — §9.3)*
