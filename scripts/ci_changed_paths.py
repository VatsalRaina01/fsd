"""Decide whether a PR's changed files need the full test suite (spec 102 A2).

Reads changed file names on stdin, one per line. Prints `false` when every file is docs
(a `*.md` file anywhere, or a file named `LICENSE` or `NOTICE`), otherwise `true`. An empty
list prints `true`: this is an allowlist of what is safe to skip, so anything unknown runs
everything.

    git diff --name-only "origin/$GITHUB_BASE_REF.." | python scripts/ci_changed_paths.py
"""
from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import PurePosixPath

DOCS_NAMES = {"LICENSE", "NOTICE"}


def is_docs(path: str) -> bool:
    p = PurePosixPath(path.strip())
    return p.suffix == ".md" or p.name in DOCS_NAMES


def needs_full_suite(paths: Iterable[str]) -> bool:
    """True unless there is at least one path and all of them are docs."""
    paths = [p for p in (s.strip() for s in paths) if p]
    return not paths or not all(is_docs(p) for p in paths)


def main() -> int:
    print("true" if needs_full_suite(sys.stdin.read().splitlines()) else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
