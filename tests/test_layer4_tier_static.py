"""Layer 4 (static): endpoints_used ⊆ tier in endpoint_tiers.yaml.

This is the static fallback while CI runs with one Alpha key. v1.1 will
add empirical per-tier probing on top of this.
"""

from __future__ import annotations

from cookbook_tools.frontmatter import Frontmatter
from cookbook_tools.tier_map import TierMap, tier_covers


def test_all_endpoints_covered_by_declared_tier(
    recipe_fm: Frontmatter, tier_map: TierMap
):
    over_tier = []
    for ep in recipe_fm.endpoints_used:
        concrete = ep.replace("{symbol}", "SPY")
        required = tier_map.required_for(concrete)
        if not tier_covers(recipe_fm.tier, required):
            over_tier.append((ep, required))
    assert not over_tier, (
        f"Recipe declares tier={recipe_fm.tier!r} but uses endpoints "
        f"that require higher tiers: {over_tier}. "
        f"Either upgrade the recipe's declared tier or add those cells "
        f"to tier_gated_cells."
    )
