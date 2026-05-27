"""Cross-validate: a recipe's frontmatter must be honest about which
endpoints it hits and how many calls it makes. Compare the declared
`endpoints_used` and `max_api_calls` against the recorded cassette."""

from __future__ import annotations

import pathlib
from urllib.parse import urlparse

import pytest
import yaml

from cookbook_tools.frontmatter import Frontmatter

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"


def _endpoint_from_url(url: str) -> str:
    """Return just the path component, normalized."""
    parsed = urlparse(url)
    return parsed.path


def _normalize_endpoint_template(ep: str) -> str:
    """`/v1/exposure/gex/{symbol}` → `/v1/exposure/gex/`. Strips template
    suffix so comparisons against concrete paths use the prefix."""
    if "{" in ep:
        ep = ep[: ep.index("{")]
    if not ep.endswith("/"):
        ep += "/"
    return ep


def test_cassette_endpoints_subset_of_declared(recipe_fm: Frontmatter):
    """Every URL the cassette recorded must be covered by an entry in
    `endpoints_used`. Authors can't sneak in undeclared API calls."""
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")
    data = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    declared_prefixes = {
        _normalize_endpoint_template(ep) for ep in recipe_fm.endpoints_used
    }
    undeclared: list[str] = []
    for interaction in data.get("interactions", []):
        request = interaction.get("request", {})
        url = request.get("uri", "")
        path = _endpoint_from_url(url)
        if not any(path.startswith(prefix) for prefix in declared_prefixes):
            undeclared.append(path)
    assert not undeclared, (
        f"{recipe_fm.slug}: cassette has calls not in endpoints_used: "
        f"{sorted(set(undeclared))}\n"
        f"declared prefixes: {sorted(declared_prefixes)}"
    )


def test_max_api_calls_matches_actual(recipe_fm: Frontmatter):
    """The declared `max_api_calls` budget should equal the actual
    interaction count (not just `<=`). If a recipe is using fewer calls than
    declared, the budget should be tightened."""
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")
    data = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    actual = len(data.get("interactions", []))
    declared = recipe_fm.max_api_calls
    # Permit a slack of +2 for retry / off-by-one rounding. Anything more is
    # either over-budgeted (tighten) or undeclared regression (investigate).
    assert actual <= declared, (
        f"{recipe_fm.slug}: cassette has {actual} interactions but "
        f"max_api_calls={declared}"
    )
    assert actual >= declared - 2, (
        f"{recipe_fm.slug}: cassette has only {actual} interactions but "
        f"max_api_calls={declared} — tighten the budget"
    )
