"""Layer 0: secret + auth-header sweep over notebook source + outputs.

Pre-commit already runs gitleaks + scrub_outputs.py. This test is the
backstop: if either fails to fire (skipped, disabled, mis-configured),
this catches the leak at PR time.
"""

from __future__ import annotations

import json
import pathlib
import re

from cookbook_tools.notebook_io import load_notebook

# Patterns matched across the FULL notebook JSON (code + markdown + outputs).
_SHAPES = [
    re.compile(r"\bfa_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    # JWT shape
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\b"),
    # OpenAI-shaped sk- key (defensive — quants might paste one)
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


def test_no_secrets_in_recipe(recipe_path: pathlib.Path):
    text = recipe_path.read_text(encoding="utf-8")
    for pat in _SHAPES:
        match = pat.search(text)
        assert match is None, (
            f"Possible secret in {recipe_path.relative_to(recipe_path.parents[2])}: "
            f"pattern={pat.pattern!r} matched={match.group()!r}"
        )


def test_no_authorization_header_value_in_outputs(recipe_path: pathlib.Path):
    """The scrubber should have stripped these. If <REDACTED> is missing
    and 'Authorization' is present with a value, the scrubber failed."""
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs", []):
            blob = json.dumps(output)
            # If the output mentions "Authorization", the value must be redacted.
            if "Authorization" in blob or "authorization" in blob:
                assert "<REDACTED>" in blob or "REDACTED" in blob, (
                    f"Unredacted Authorization header in output of "
                    f"{recipe_path.name}: {blob[:200]}"
                )
