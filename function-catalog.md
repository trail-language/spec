# Trail Function Catalog

A survey of standard mathematical, statistical, calculus, geometry, and transformation
functions, classified by how each fits Trail's execution model. Three tiers:

- **P - Primitive.** Irreducible: introduces windowing, cross-sectional reduction, or a
  transcendental that cannot be composed from `{+ - * / ^, sqrt, abs, log, exp}`. Implemented
  on the columnar engine (`ops.py`).
- **D - Derived.** A pure composition of primitives (and other derived functions). Written
  **in Trail** as a `def` macro in `trail/stdlib/*.trail`; no engine code.
- **R - Registered.** Needs matrix algebra, iteration, or state - the whitelisted Python
  escape hatch.

Everything marked **D** below is implemented and tested (`tests/test_stdlib.py` expands all stdlib macros
(tests expand every stdlib macro to primitives). Everything marked **P** is a live primitive. **R** items are noted for later.

---

## 1. Elementary math

| Function | Tier | Definition / note |
|---|---|---|
| `+ - * / % ^` | core | operators (grammar) |
| `abs`, `sqrt` | P | scalar primitives |
| `sign(x)` | D | `1 if x>0 else -1 if x<0 else 0` |
| `square(x)`, `cube(x)` | D | `x*x`, `x*x*x` |
| `reciprocal(x)` | D | `1/x` |
| `cbrt(x)` | D | `sign(x) * abs(x)^(1/3)` (handles negatives) |
| `hypot(a,b)` | D | `sqrt(a*a + b*b)` |
| `floor`, `ceil`, `round` | P | rounding primitives |
| `min(a,b)`, `max(a,b)`, `clamp(x,lo,hi)` | P | cell-wise |
| `clip_lower/clip_upper` | D | `max(x,lo)` / `min(x,hi)` |

## 2. Exponential & logarithmic

| Function | Tier | Definition |
|---|---|---|
| `exp`, `log` (natural) | P | primitives |
| `log10`, `log2`, `logb(x,b)` | D | `log(x)/log(base)` |
| `log1p(x)`, `expm1(x)` | D | `log(1+x)`, `exp(x)-1` |
| `pow10(x)` | D | `10 ^ x` |
| `sigmoid`, `logit`, `softplus` | D | `1/(1+exp(-x))`, `log(p/(1-p))`, `log(1+exp(x))` |

## 3. Hyperbolic

| Function | Tier | Definition |
|---|---|---|
| `sinh`, `cosh`, `tanh` | D | via `exp` (e.g. `tanh = (exp(2x)-1)/(exp(2x)+1)`); overflow for very large \|x\| |
| `asinh`, `acosh`, `atanh` | D | via `log`/`sqrt` |

## 4. Trigonometry

| Function | Tier | Note |
|---|---|---|
| `sin`, `cos`, `tan` | P | **primitive** - genuinely transcendental, not composable from exp of real args |
| `asin`, `acos`, `atan` | P | primitive |
| `atan2(y,x)` | R/P | quadrant logic; add `arctan2` primitive when needed |
| `pi()`, `tau()`, `euler()` | D | zero-arg constant macros |
| `deg2rad`, `rad2deg` | D | `x*pi()/180`, `x*180/pi()` |

## 5. Statistics - cross-sectional (within period[, `by` group])

| Function | Tier | Definition |
|---|---|---|
| `xs_mean/median/sum` | P | reducers (existing) |
| `xs_std/var/min/max/count` | P | reducers (added) |
| `xs_quantile(x,q)` | P | reducer |
| `zscore`, `rank`, `winsorize` | P | standardize / order / clip |
| `pctile(x)` | D | `(rank(x)-1)/(xs_count(x)-1)` (migrated to stdlib) |
| `xs_frac(cond)` | P | fraction true |
| `demean(x)` | D | `x - xs_mean(x)` |
| `xs_range`, `xs_cv` | D | `xs_max-xs_min`, `xs_std/xs_mean` |
| `minmax(x)` | D | `(x-xs_min)/(xs_max-xs_min)` |
| `xs_mad(x)` | D | `xs_median(abs(x-xs_median(x)))` |
| `robust_zscore(x)` | D | `(x-xs_median)/(1.4826*xs_mad)` |
| `ntile(x,k)`, `neutralize(x,f)` | D | quantile bucketing, single-factor residual (stdlib/factor.trail) |
| `rank_gauss` | R | rank→normal (needs probit) |

## 6. Statistics - time-series (per security, trailing window)

| Function | Tier | Definition |
|---|---|---|
| `roll_mean/sum/std/var/max/min/quantile` | P | rolling reducers |
| `roll_median`, `roll_skew` | P | added |
| `roll_cov`, `roll_corr`, `beta` | D | migrated to stdlib/timeseries.trail (compositions of roll_mean/roll_var) |
| `roll_zscore`, `roll_range`, `roll_cv` | D | rolling standardize / range / CoV |
| `roll_geomean(x,n)` | D | `exp(roll_mean(log(x),n))` |
| `autocorr(x,k,n)` | D | `roll_corr(x, lag(x,k), n)` |
| `ewm_mean`, `ewm_std` | P | implemented (decay recurrence); `roll_kurt` future |

## 7. Calculus (finite-difference, over the causal period axis)

| Function | Tier | Definition |
|---|---|---|
| `lag`, `cumsum`, `cumprod`, `cummin`, `cummax` | P | shift + cumulative primitives |
| `diff(x)` | D | `x - lag(x,1)` (backward derivative) |
| `diff2(x)` | D | `x - 2*lag(x,1) + lag(x,2)` |
| `deriv(x,n)` | D | `(x - lag(x,n))/n` |
| `pct_change`, `momentum`, `log_return` | D | rate of change / difference / `log(x)-log(lag(x,1))` |
| `integral(x)` | D | `cumsum(x)` (rectangular) |
| `trapz(x)` | D | `cumsum((x+lag(x,1))/2)` (trapezoidal) |
| `cum_return(r)` | D | `cumprod(1+r) - 1` |
| central differences, forward integrals | ✗ | **excluded** - reference the future (I4) |

## 8. Geometry

| Function | Tier | Definition |
|---|---|---|
| `hypot(a,b)` | D | `sqrt(a*a+b*b)` |
| `dist2`, `manhattan` | D | pairwise Euclidean / L1 distance |
| angles, rotations | P | need trig primitives (sin/cos/atan2) |
| vector norms across securities | R | cross-entity / matrix shape |

## 9. Transformations & feature encodings

| Function | Tier | Definition |
|---|---|---|
| `signed_log(x)` | D | `sign(x)*log1p(abs(x))` |
| `signed_power(x,a)` | D | `sign(x)*abs(x)^a` |
| `to_bps`, `to_pct` | D | `x*10000`, `x*100` |
| `indicator(cond)` | D | `1 if cond else 0` |
| `between(x,lo,hi)` | D | `x>=lo and x<=hi` |
| `decay_linear` | P | implemented (linearly-weighted rolling) |
| `scale(x)` | D | L1-normalize, `x/xs_sum(abs(x))` (stdlib/factor.trail) |
| `rank_gauss` | R | rank→normal (needs probit) |

## 10. Distributions

| Function | Tier | Note |
|---|---|---|
| `normal_pdf(x)` | D | `exp(-x*x/2)/sqrt(2*pi())` |
| `normal_cdf(x)` | D | via a polynomial (Abramowitz-Stegun) approximation over `exp` |
| `erf`, exact `normal_cdf`, `t`/`chi2` CDFs | R | special functions |

## 11. Registered tier (out of scope for macros)

Multivariate/OLS regression & residuals (IVOL, neutralization), covariance/correlation
**matrices**, PCA/eigen-portfolios, Kalman/HP filters, GARCH, STL decomposition, Box-Cox
with fitted λ, IRR/YTM root-finding, optimizers. Each is vectorizable *internally* but is
neither a primitive nor a composition - the Python escape hatch (`§7.6`).

---

## The lesson

Of the standard-function surface, the overwhelming majority is **derived** - pure composition
of a small primitive core (48 primitives: shift, the rolling and cross-sectional reducers,
scalar `sqrt/log/exp`, trig, rounding, and the cumulative ops). The 78 functions in
`stdlib/*.trail` are all Trail source. Only genuine transcendentals (trig), irreducible
reductions (windows, cross-sections), and matrix/iterative methods need engine code. That is
the payoff of the primitive/derived split: the language and its engine stay tiny; the library
grows in Trail.
