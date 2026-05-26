"""Tests for the Frontmatter Pydantic schema."""

import textwrap

import pytest
from pydantic import ValidationError

from cookbook_tools.frontmatter import Frontmatter, parse_frontmatter

VALID_YAML = textwrap.dedent("""\
    ---
    slug: 01-gex-dashboard
    title: Build a GEX Dashboard in 30 Lines
    tier: free
    runtime_budget_seconds: 60
    max_api_calls: 8
    endpoints_used:
      - /v1/exposure/gex/{symbol}
      - /v1/exposure/levels/{symbol}
    tier_gated_cells: []
    sdk_version_min: "1.0.1"
    utm_campaign: 01-gex-dashboard
    expected_artifacts:
      dataframes: []
      charts: [gex_chart.png]
    last_validated_live: 2026-05-25
    ---
""")


def test_parse_valid_frontmatter_returns_model():
    fm = parse_frontmatter(VALID_YAML)
    assert fm.slug == "01-gex-dashboard"
    assert fm.tier == "free"
    assert fm.utm_campaign == "01-gex-dashboard"
    assert fm.endpoints_used == [
        "/v1/exposure/gex/{symbol}",
        "/v1/exposure/levels/{symbol}",
    ]


def test_parse_missing_triple_dashes_raises():
    with pytest.raises(ValueError, match="frontmatter delimiter"):
        parse_frontmatter("slug: foo\ntier: free\n")


def test_invalid_tier_rejected():
    bad = VALID_YAML.replace("tier: free", "tier: nope")
    with pytest.raises(ValidationError):
        parse_frontmatter(bad)


def test_slug_must_match_utm_campaign():
    bad = VALID_YAML.replace(
        "utm_campaign: 01-gex-dashboard", "utm_campaign: something-else"
    )
    with pytest.raises(ValidationError, match="utm_campaign must equal slug"):
        parse_frontmatter(bad)


def test_slug_kebab_case_only():
    bad = VALID_YAML.replace("slug: 01-gex-dashboard", "slug: 01_gex_dashboard")
    # Also fix the utm_campaign so we test slug rules, not the cross-check.
    bad = bad.replace(
        "utm_campaign: 01-gex-dashboard", "utm_campaign: 01_gex_dashboard"
    )
    with pytest.raises(ValidationError, match="kebab-case"):
        parse_frontmatter(bad)


def test_runtime_budget_must_be_positive():
    bad = VALID_YAML.replace("runtime_budget_seconds: 60", "runtime_budget_seconds: 0")
    with pytest.raises(ValidationError):
        parse_frontmatter(bad)


def test_empty_tier_gated_cells_means_no_gates():
    fm = parse_frontmatter(VALID_YAML)
    assert fm.tier_gated_cells == []
