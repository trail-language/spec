# Versioning

The Trail specification is versioned with [Semantic Versioning](https://semver.org) as
`MAJOR.MINOR.PATCH`, applied to the **language as a contract** (grammar, semantics, standard
library, diagnostics).

- **MAJOR** - a breaking change: a program that was valid and well-defined under the previous
  version parses differently, changes meaning, or becomes invalid. Examples: removing or
  repurposing a keyword, changing an operator's precedence or an existing function's semantics,
  removing a standard-library function.
- **MINOR** - a backward-compatible addition: new syntax that doesn't change existing programs,
  new primitives or standard-library functions, newly specified (previously reserved) behavior,
  new diagnostics.
- **PATCH** - clarifications and corrections with no effect on conforming programs: wording,
  examples, non-normative notes, editorial fixes.

## Conformance phases vs. versions

The reference (`reference.md`) defines **conformance phases** (1-4) describing which constructs
an implementation executes. Phases are a roadmap, not the version: a construct may be *specified*
(and parse) in an early version while its *execution* lands in a later phase. Moving a construct
from "parses" to "executes" is a MINOR change; changing already-executing behavior is MAJOR.

## Releases

Each release is a git tag `vMAJOR.MINOR.PATCH` with a dated entry summarizing the change and its
version-class (major/minor/patch). The reference implementation
([`trail-py`](https://github.com/trail-language/trail-py)) declares the highest spec version it
conforms to.

## Standard library

The canonical standard library lives in [`stdlib/`](stdlib/). Adding a function is MINOR;
changing an existing function's result or removing one is MAJOR. Implementations vendor a copy
and are expected to track it exactly.
