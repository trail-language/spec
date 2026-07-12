#!/usr/bin/env python3
"""Validate the canonical standard library against the reference implementation (trail-py).

Confirms that every stdlib function parses, has a unique name, is non-recursive, and expands
to engine PRIMITIVES only (no dangling references). Exits non-zero on any problem.
"""
from __future__ import annotations

import glob
import sys

try:
    from trail import ast
    from trail.macro import collect_functions, expand
    from trail.parser import parse_program
    from trail.validate import KNOWN_FUNCTIONS
except ImportError:
    sys.exit(
        "trail-py (the reference implementation) is required:\n"
        "  pip install 'trail-lang @ git+https://github.com/trail-language/trail-py.git'"
    )


def _call_names(e, acc: set[str]) -> None:
    match e:
        case ast.Call():
            acc.add(e.name)
            for a in e.args:
                _call_names(a, acc)
        case ast.BinOp() | ast.Compare() | ast.BoolOp() | ast.Coalesce():
            _call_names(e.left, acc)
            _call_names(e.right, acc)
        case ast.Not() | ast.Neg():
            _call_names(e.operand, acc)
        case ast.In():
            _call_names(e.item, acc)
        case ast.Ternary():
            _call_names(e.value, acc)
            _call_names(e.cond, acc)
            _call_names(e.orelse, acc)


def main() -> None:
    files = sorted(glob.glob("stdlib/*.trail"))
    if not files:
        sys.exit("no stdlib/*.trail files found (run from the repo root)")
    src = "\n".join(open(f).read() for f in files)
    funcs = collect_functions(parse_program(src))  # raises on duplicate names

    problems = 0
    for name, fd in funcs.items():
        call = ast.Call(name, tuple(ast.Literal(2.0) for _ in fd.params))
        try:
            expanded = expand(call, funcs)  # raises on recursion / arity mismatch
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name}: {e}")
            problems += 1
            continue
        acc: set[str] = set()
        _call_names(expanded, acc)
        leftover = acc - set(KNOWN_FUNCTIONS)
        if leftover:
            print(f"FAIL {name}: expands to non-primitives {sorted(leftover)}")
            problems += 1

    print(f"checked {len(funcs)} functions across {len(files)} file(s)")
    if problems:
        sys.exit(f"{problems} problem(s) found")
    print("standard library OK")


if __name__ == "__main__":
    main()
