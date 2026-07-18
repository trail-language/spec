<p align="center">
  <img src="brand/icon-color-240.png" alt="Trail" width="120">
</p>

# Trail - Language Specification

**Trail** (Tabular Ratios, Analytics & Indicator Language) is a small, total, declarative
language for computing financial indicators, scores, and screening strategies over panels of
securities. Expressions are data - written and validated by both humans and AI agents - and
compile to vectorized columnar operations.

```trail
model quality on us_main at annual {
    operating_margin = income.operating_income / income.revenue
    score om_score weight 7 {
        2 if operating_margin > 0.12
        1 if operating_margin > 0.05
        else 0
    }
    export composite = weighted_score()
}
```

This repository is the **versioned specification** - the normative definition of the language.
The reference implementation lives in [`trail-py`](https://github.com/trail-language/trail-py).

## Contents

| Path | What |
|---|---|
| [`grammar/trail.ebnf`](grammar/trail.ebnf) | The normative grammar (EBNF). |
| [`grammar/trail.lark`](grammar/trail.lark) | The same grammar in Lark form (drives the reference parser). |
| [`reference.md`](reference.md) | The language reference: data model, semantics, functions, declarations, diagnostics, config. |
| [`function-catalog.md`](function-catalog.md) | Every standard function, classified primitive / derived / registered. |
| [`stdlib/`](stdlib/) | The canonical standard library - derived functions written in Trail itself. |
| [`VERSIONING.md`](VERSIONING.md) | How this specification is versioned. |

## The two-layer model

The language is tiny; the library is large and written in Trail:

- **Primitives** - irreducible operations (windowing, cross-sectional reduction, scalar math)
  implemented by an engine. These cannot be expressed by composition.
- **Derived functions** - pure compositions of primitives, written as `def` macros in
  [`stdlib/`](stdlib/). Most of the financial and statistical surface lives here.

See [`function-catalog.md`](function-catalog.md) for the full classification.

## Status

**Version 1.0.0.** The 1.0 core is normative and executes: expressions and built-ins,
`universe` / `model` / `score` / `signal`, user-defined functions, the standard library,
`import` source-level inclusion, multi-source resolution with per-cell coalescing and the
`@` field-reference qualifiers (`@ source` / `@ entity` / `@ align`), point-in-time
cross-frequency alignment, the temporal operators, the data-source contract, and runtime
configuration. `strategy` / `backtest` / `learn` execution, the `@ asof` / `@ params`
qualifiers, and registered functions parse-or-are-reserved as post-1.0 extension points
(see §1.2 and Appendix B in [`reference.md`](reference.md)).

## License

[MIT](LICENSE).
