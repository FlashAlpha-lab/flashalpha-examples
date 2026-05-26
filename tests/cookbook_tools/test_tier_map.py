"""Tests for endpoint→tier lookup."""

import pathlib

import pytest

from cookbook_tools.tier_map import (
    TIER_ORDER,
    TierMap,
    load_tier_map,
    tier_covers,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TIER_MAP_PATH = REPO_ROOT / "endpoint_tiers.yaml"


@pytest.fixture(scope="module")
def tier_map() -> TierMap:
    return load_tier_map(TIER_MAP_PATH)


def test_loads_without_error(tier_map: TierMap):
    assert len(tier_map.rules) > 0


def test_gex_endpoint_is_free(tier_map: TierMap):
    assert tier_map.required_for("/v1/exposure/gex/SPY") == "free"


def test_volatility_endpoint_is_growth(tier_map: TierMap):
    assert tier_map.required_for("/v1/volatility/SPY") == "growth"


def test_vrp_endpoint_is_alpha(tier_map: TierMap):
    assert tier_map.required_for("/v1/vrp/SPY") == "alpha"


def test_flow_levels_is_growth_not_alpha(tier_map: TierMap):
    """Most-specific match wins: /v1/flow/levels/ is growth even though
    /v1/flow/ catch-all is alpha."""
    assert tier_map.required_for("/v1/flow/levels/SPY") == "growth"


def test_flow_history_is_alpha_catchall(tier_map: TierMap):
    """/v1/flow/history/ has no specific rule, so the /v1/flow/ catch-all
    (alpha) applies."""
    assert tier_map.required_for("/v1/flow/history/SPY") == "alpha"


def test_unknown_endpoint_falls_through_to_free(tier_map: TierMap):
    """The /v1/ catch-all at the bottom makes any /v1/* path free unless
    a more-specific rule wins. Endpoints outside /v1 raise."""
    with pytest.raises(KeyError):
        tier_map.required_for("/random/path")


def test_tier_covers_ordering():
    assert tier_covers("alpha", "free")
    assert tier_covers("growth", "growth")
    assert tier_covers("growth", "basic")
    assert not tier_covers("free", "growth")
    assert not tier_covers("basic", "alpha")


def test_tier_order_is_strict():
    assert TIER_ORDER == ("free", "basic", "growth", "alpha")
