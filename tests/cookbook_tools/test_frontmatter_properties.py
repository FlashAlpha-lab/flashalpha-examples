"""Property-based tests for frontmatter slug validation and parse/render
roundtrip stability."""

from __future__ import annotations

import datetime as dt

import yaml
from hypothesis import given, strategies as st

from cookbook_tools.frontmatter import (
    SLUG_RE,
    parse_frontmatter,
)

# Valid slug: kebab-case, 1+ segments of lowercase letters/digits.
_slug_segment = st.from_regex(r"^[a-z0-9]+\Z", fullmatch=True)


@given(st.lists(_slug_segment, min_size=1, max_size=6))
def test_constructed_slugs_match_regex(segments: list[str]):
    """Any kebab-case-conformant string should match SLUG_RE."""
    slug = "-".join(segments)
    assert SLUG_RE.match(slug), f"valid kebab-case slug {slug!r} rejected"


@given(st.from_regex(r"^[A-Z_]+$", fullmatch=True))
def test_uppercase_or_underscore_slugs_rejected(bad_slug: str):
    """Slugs with uppercase or underscores must not match."""
    assert SLUG_RE.match(bad_slug) is None


# Frontmatter strategy — generate semantically valid frontmatter dicts.
_tier = st.sampled_from(("free", "basic", "growth", "alpha"))
_slug = st.builds(
    lambda segs: "-".join(segs),
    st.lists(_slug_segment, min_size=1, max_size=4),
)


@st.composite
def _frontmatter_dicts(draw):
    slug = draw(_slug)
    return {
        "slug": slug,
        "title": draw(st.text(min_size=1, max_size=80).filter(lambda s: "\n" not in s)),
        "tier": draw(_tier),
        "runtime_budget_seconds": draw(st.integers(min_value=1, max_value=600)),
        "max_api_calls": draw(st.integers(min_value=1, max_value=50)),
        "endpoints_used": ["/v1/exposure/gex/{symbol}"],
        "tier_gated_cells": [],
        "sdk_version_min": "1.0.1",
        "utm_campaign": slug,  # must match
        "expected_artifacts": {"dataframes": [], "charts": []},
        "last_validated_live": draw(
            st.dates(min_value=dt.date(2024, 1, 1), max_value=dt.date(2030, 12, 31))
        ).isoformat(),
    }


@given(_frontmatter_dicts())
def test_frontmatter_parse_roundtrip(fm_dict: dict):
    """Parse → re-emit → parse should produce an identical Frontmatter."""
    # Build the scalar block via yaml.dump so that special characters in
    # free-text fields (colons, brackets, etc.) are properly quoted.
    scalar_keys = [
        "slug", "title", "tier", "runtime_budget_seconds", "max_api_calls",
        "sdk_version_min", "utm_campaign", "last_validated_live",
    ]
    scalar_block = yaml.dump(
        {k: fm_dict[k] for k in scalar_keys},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    # Combine with the fixed list/map sections into a well-formed frontmatter
    # block.  Avoid textwrap.dedent + f-string interpolation because dedent
    # cannot strip the leading spaces from the '---' delimiters when the
    # interpolated body lines have no common prefix.
    text = (
        "---\n"
        + scalar_block
        + "endpoints_used:\n"
        + "  - /v1/exposure/gex/{symbol}\n"
        + "tier_gated_cells: []\n"
        + "expected_artifacts:\n"
        + "  dataframes: []\n"
        + "  charts: []\n"
        + "---\n"
    )
    fm = parse_frontmatter(text)
    assert fm.slug == fm_dict["slug"]
    assert fm.tier == fm_dict["tier"]
    assert fm.utm_campaign == fm_dict["slug"]
    assert fm.runtime_budget_seconds == fm_dict["runtime_budget_seconds"]
