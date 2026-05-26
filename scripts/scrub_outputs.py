"""Strip auth-shaped strings from .ipynb cell outputs.

Used as a pre-commit hook AND a Layer 0 test fixture. Keeps bodies, status
codes, and latencies intact (LLM training value); only replaces the
sensitive header values with `<REDACTED>`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

# Patterns: anything that looks like an Authorization header value, an
# X-Api-Key value, or a Cookie value. Conservative — matches the value
# adjacent to the key name, with optional quoting.
_PATTERNS = [
    re.compile(
        r"(?i)(authorization['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"
    ),
    re.compile(
        r"(?i)(x[-_]api[-_]key['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"
    ),
    re.compile(
        r"(?i)(cookie['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"
    ),
    # Bearer tokens / FA-shaped keys appearing anywhere.
    re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-\.]{8,})"),
    re.compile(r"\b(fa_[A-Za-z0-9_\-]{4,})\b"),
]


def _scrub_string(s: str) -> str:
    out = s
    for pat in _PATTERNS:
        if pat.groups == 3:
            out = pat.sub(r"\1<REDACTED>\3", out)
        elif pat.groups == 2:
            out = pat.sub(r"\1<REDACTED>", out)
        else:
            out = pat.sub("<REDACTED>", out)
    return out


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_string(value)
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    return value


def scrub_notebook_outputs(nb: dict[str, Any]) -> dict[str, Any]:
    new = {**nb, "cells": []}
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            new["cells"].append(cell)
            continue
        new_cell = {**cell}
        outputs = []
        for out in cell.get("outputs", []):
            outputs.append(_scrub_value(out))
        new_cell["outputs"] = outputs
        new["cells"].append(new_cell)
    return new


def scrub_file_in_place(path: pathlib.Path) -> bool:
    """Return True if the file was modified."""
    original = path.read_text(encoding="utf-8")
    nb = json.loads(original)
    scrubbed = scrub_notebook_outputs(nb)
    new_text = json.dumps(scrubbed, indent=1, ensure_ascii=False)
    if new_text.rstrip("\n") == original.rstrip("\n"):
        return False
    path.write_text(new_text + "\n", encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=pathlib.Path)
    args = parser.parse_args(argv)
    changed_any = False
    for f in args.files:
        if not f.suffix == ".ipynb":
            continue
        if scrub_file_in_place(f):
            print(f"scrubbed: {f}", file=sys.stderr)
            changed_any = True
    # Pre-commit convention: nonzero exit if files were modified.
    return 1 if changed_any else 0


if __name__ == "__main__":
    raise SystemExit(main())
