"""Property-based tests for CTA renderer invariants."""

from __future__ import annotations

import datetime as dt

from hypothesis import given, strategies as st

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_gate_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import ExpectedArtifacts, Frontmatter

_slug = st.from_regex(r"^[a-z0-9]+(-[a-z0-9]+){0,3}\Z", fullmatch=True)
_tier = st.sampled_from(("free", "basic", "growth", "alpha"))
_tier_dir = st.sampled_from((
    "tier-a-hooks", "tier-b-dealer-flow", "tier-c-vol-surface",
    "tier-d-0dte", "tier-e-flow", "tier-f-backtest", "tier-g-engineering",
))


@st.composite
def _frontmatters(draw):
    slug = draw(_slug)
    return Frontmatter(
        slug=slug,
        title=draw(
            st.text(min_size=1, max_size=60).filter(lambda s: "\n" not in s)
        ),
        tier=draw(_tier),
        runtime_budget_seconds=draw(st.integers(min_value=1, max_value=600)),
        max_api_calls=draw(st.integers(min_value=1, max_value=50)),
        endpoints_used=["/v1/exposure/gex/{symbol}"],
        tier_gated_cells=[],
        sdk_version_min="1.0.1",
        utm_campaign=slug,
        expected_artifacts=ExpectedArtifacts(),
        last_validated_live=dt.date.today(),
    )


@given(_frontmatters(), _tier_dir)
def test_top_cell_always_contains_signup_url_with_correct_utm(
    fm: Frontmatter, tier_dir: str
):
    md = render_top_cell(fm, tier_dir=tier_dir)
    assert f"utm_campaign={fm.slug}" in md
    assert "flashalpha.com/signup" in md
    assert f"notebooks/{tier_dir}/{fm.slug}.ipynb" in md


@given(_frontmatters())
def test_bottom_cell_always_contains_all_four_links(fm: Frontmatter):
    md = render_bottom_cell(fm)
    assert "flashalpha.com/pricing" in md
    assert "flashalpha.com/discord" in md
    assert "github.com/FlashAlpha-lab/flashalpha-examples" in md
    assert "flashalpha.com/docs/mcp" in md
    assert f"utm_campaign={fm.slug}" in md


@given(_frontmatters(), _tier)
def test_gate_cell_names_endpoint_and_required_tier(
    fm: Frontmatter, required_tier: str
):
    md = render_gate_cell(
        endpoint="/v1/example/foo", required_tier=required_tier, fm=fm
    )
    assert "/v1/example/foo" in md
    assert f"**{required_tier}+**" in md
    assert f"utm_campaign={fm.slug}" in md
