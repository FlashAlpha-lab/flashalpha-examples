"""Tests for CTA markdown rendering."""

import datetime as dt

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_gate_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import Frontmatter, ExpectedArtifacts


def _fm(tier="free", slug="01-gex-dashboard"):
    return Frontmatter(
        slug=slug,
        title="Build a GEX Dashboard in 30 Lines",
        tier=tier,
        runtime_budget_seconds=60,
        max_api_calls=8,
        endpoints_used=["/v1/exposure/gex/{symbol}"],
        tier_gated_cells=[],
        sdk_version_min="1.0.1",
        utm_campaign=slug,
        expected_artifacts=ExpectedArtifacts(dataframes=[], charts=["gex_chart.png"]),
        last_validated_live=dt.date(2026, 5, 25),
    )


def test_top_cell_contains_signup_url_with_utm():
    md = render_top_cell(_fm(), tier_dir="tier-a-hooks")
    assert "# Build a GEX Dashboard in 30 Lines" in md
    assert (
        "https://flashalpha.com/signup?utm_source=github-cookbook"
        "&utm_medium=notebook&utm_campaign=01-gex-dashboard"
        in md
    )
    assert "Tier required: **Free**" in md
    assert (
        "https://colab.research.google.com/github/FlashAlpha-lab/"
        "flashalpha-examples/blob/main/notebooks/tier-a-hooks/01-gex-dashboard.ipynb"
        in md
    )


def test_top_cell_growth_tier_display_name():
    fm = _fm(tier="growth")
    md = render_top_cell(fm, tier_dir="tier-b-dealer-flow")
    assert "Tier required: **Growth**" in md


def test_bottom_cell_contains_all_four_bullets():
    md = render_bottom_cell(_fm())
    for needle in [
        "Backtest this with historical replay",
        "https://flashalpha.com/pricing?utm_source=github-cookbook"
        "&utm_campaign=01-gex-dashboard",
        "https://flashalpha.com/discord",
        "https://github.com/FlashAlpha-lab/flashalpha-examples",
        "https://flashalpha.com/docs/mcp",
    ]:
        assert needle in md


def test_gate_cell_names_endpoint_and_required_tier():
    md = render_gate_cell(
        endpoint="/v1/vrp/SPY", required_tier="alpha", fm=_fm(tier="growth")
    )
    assert "`/v1/vrp/SPY`" in md
    assert "**alpha+**" in md
    assert (
        "https://flashalpha.com/pricing?utm_source=github-cookbook"
        "&utm_campaign=01-gex-dashboard" in md
    )
    assert "growth users will get a 403" in md.lower()
