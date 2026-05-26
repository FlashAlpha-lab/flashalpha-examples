"""Render the three structurally-enforced CTA markdown cells from frontmatter."""

from __future__ import annotations

from .frontmatter import Frontmatter
from .tier_map import Tier

_TIER_DISPLAY = {
    "free": "Free",
    "basic": "Basic",
    "growth": "Growth",
    "alpha": "Alpha",
}

_SIGNUP_URL = (
    "https://flashalpha.com/signup"
    "?utm_source=github-cookbook&utm_medium=notebook&utm_campaign={slug}"
)
_PRICING_URL = (
    "https://flashalpha.com/pricing"
    "?utm_source=github-cookbook&utm_campaign={slug}"
)
_COLAB_URL = (
    "https://colab.research.google.com/github/FlashAlpha-lab/"
    "flashalpha-examples/blob/main/notebooks/{tier_dir}/{slug}.ipynb"
)
_COLAB_BADGE = "https://colab.research.google.com/assets/colab-badge.svg"


def render_top_cell(fm: Frontmatter, *, tier_dir: str) -> str:
    return (
        f"# {fm.title}\n"
        f"\n"
        f"> \U0001f511 Get a free FlashAlpha API key (5 req/day, no card):\n"
        f">   {_SIGNUP_URL.format(slug=fm.slug)}\n"
        f">\n"
        f"> Tier required: **{_TIER_DISPLAY[fm.tier]}** · "
        f"[![Open in Colab]({_COLAB_BADGE})]"
        f"({_COLAB_URL.format(tier_dir=tier_dir, slug=fm.slug)})\n"
    )


def render_bottom_cell(fm: Frontmatter) -> str:
    pricing = _PRICING_URL.format(slug=fm.slug)
    return (
        "## What to try next\n"
        "\n"
        f"- \U0001f501 Backtest this with historical replay (Alpha) → {pricing}\n"
        "- \U0001f4ac Discord: https://flashalpha.com/discord\n"
        "- \U0001f4da More recipes: https://github.com/FlashAlpha-lab/flashalpha-examples\n"
        "- \U0001f916 Use with Claude/Cursor via MCP: https://flashalpha.com/docs/mcp\n"
    )


def render_gate_cell(
    *, endpoint: str, required_tier: Tier, fm: Frontmatter
) -> str:
    pricing = _PRICING_URL.format(slug=fm.slug)
    return (
        f"> \U0001f512 The next call uses `{endpoint}` which requires "
        f"**{required_tier}+**.\n"
        f"> Free/{fm.tier} users will get a 403 here.\n"
        f"> Upgrade: {pricing}\n"
    )
