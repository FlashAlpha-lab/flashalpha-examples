"""Pydantic schema for cookbook recipe frontmatter.

Every recipe (`notebooks/tier-*/<slug>.ipynb`) begins with a raw cell
containing YAML between `---` delimiters. This module parses and validates
that block. The field descriptions below are the single source of truth —
`docs/frontmatter-schema.md` is auto-generated from them.
"""

from __future__ import annotations

import re
from datetime import date

import yaml
from pydantic import BaseModel, Field, model_validator

from .tier_map import Tier

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ExpectedArtifacts(BaseModel):
    """Artifacts the recipe is declared to produce. Layer 3 (Phase 6) uses
    these names to look up golden-snapshot files under `snapshots/<slug>/`."""

    dataframes: list[str] = Field(
        default_factory=list,
        description=(
            "Names of pandas DataFrames the recipe stores into the cell "
            "namespace. Each name resolves to "
            "`snapshots/<slug>/<name>.csv` for Layer 3 golden-value "
            "comparison. Empty for live-data (non-deterministic) recipes."
        ),
    )
    charts: list[str] = Field(
        default_factory=list,
        description=(
            "Filenames the recipe writes via `fig.savefig(name)`. Each "
            "name resolves to `snapshots/<slug>/<name>` for Layer 3 "
            "perceptual-hash comparison."
        ),
    )


class Frontmatter(BaseModel):
    """The structurally enforced metadata block at the top of every recipe.

    Authors do NOT write this by hand — `scripts/new_recipe.py` scaffolds
    it from CLI args. Layer 1 (structural test) enforces that every field
    is present and valid on every commit."""

    slug: str = Field(
        description=(
            "Kebab-case identifier, must match the filename stem and the "
            "UTM campaign. Used as the recipe's primary key across "
            "cassettes, snapshots, and analytics."
        ),
    )
    title: str = Field(
        description=(
            "Human-readable title shown as the H1 of the recipe's top "
            "markdown cell. Should be short enough to fit in a Colab tab "
            "(~60 chars). Markdown-special characters are allowed."
        ),
    )
    tier: Tier = Field(
        description=(
            "Minimum FlashAlpha subscription tier required to run the "
            "recipe end-to-end. One of: free, basic, growth, alpha. The "
            "tier display name (Free/Basic/Growth/Alpha) appears in the "
            "top CTA cell. Layer 4 asserts every endpoint in "
            "`endpoints_used` resolves to a tier ≤ this value, OR the "
            "calling cell is listed in `tier_gated_cells`."
        ),
    )
    runtime_budget_seconds: int = Field(
        gt=0,
        description=(
            "Maximum wall-clock seconds the recipe is allowed to run "
            "under Layer 2 cassette replay. Exceeding this fails the PR "
            "build. Tighten as the recipe matures; default 60s."
        ),
    )
    max_api_calls: int = Field(
        gt=0,
        description=(
            "Maximum number of FlashAlpha API interactions the recipe is "
            "allowed to make. Layer 2 asserts the cassette interaction "
            "count is ≤ this value (and ≥ value-2 to prevent budget "
            "padding)."
        ),
    )
    endpoints_used: list[str] = Field(
        description=(
            "FlashAlpha API path templates the recipe calls. `{symbol}` "
            "is substituted with `SPY` for tier lookups. Layer 4 asserts "
            "every entry resolves to a known tier in "
            "`endpoint_tiers.yaml`, and that the resolved tier is ≤ "
            "`tier`."
        ),
    )
    tier_gated_cells: list[int] = Field(
        default_factory=list,
        description=(
            "Cell indices (0-based) that intentionally call an endpoint "
            "above the recipe's declared tier. Each such cell must be "
            "preceded by a mid-gate markdown cell matching "
            "`render_gate_cell(endpoint, required_tier, fm)`. Empty for "
            "tier-conforming recipes."
        ),
    )
    sdk_version_min: str = Field(
        description=(
            "Minimum `flashalpha` SDK version the recipe depends on. "
            "Used by the on-sdk-release dispatch workflow (Phase 1+) to "
            "decide which recipes to re-validate after an SDK bump."
        ),
    )
    utm_campaign: str = Field(
        description=(
            "UTM campaign string embedded in every CTA URL in the "
            "recipe. MUST equal `slug` — Layer 1 enforces. Lets the "
            "marketing funnel attribute signups back to the specific "
            "recipe that drove them."
        ),
    )
    expected_artifacts: ExpectedArtifacts = Field(
        default_factory=ExpectedArtifacts,
        description=(
            "Names of DataFrames and chart files the recipe produces. "
            "Layer 3 (Phase 6) reads these to look up golden snapshots. "
            "Leave empty for live-data recipes; populate for "
            "deterministic backtest recipes."
        ),
    )
    last_validated_live: date = Field(
        description=(
            "Date (YYYY-MM-DD) the recipe was last successfully executed "
            "against the live API. Updated by the nightly drift job. "
            "Recipes whose date is >30 days stale appear in the weekly "
            "freshness report."
        ),
    )

    @model_validator(mode="after")
    def _check_slug_kebab_case(self) -> "Frontmatter":
        if not SLUG_RE.match(self.slug):
            raise ValueError(
                f"slug {self.slug!r} must be kebab-case (lowercase, digits, hyphens)"
            )
        return self

    @model_validator(mode="after")
    def _check_utm_matches_slug(self) -> "Frontmatter":
        if self.utm_campaign != self.slug:
            raise ValueError(
                f"utm_campaign must equal slug: got "
                f"utm_campaign={self.utm_campaign!r}, slug={self.slug!r}"
            )
        return self


def parse_frontmatter(text: str) -> Frontmatter:
    """Parse YAML between the first pair of `---` delimiters into a Frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter '---'")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter '---'") from exc
    body = "\n".join(lines[1:end])
    raw = yaml.safe_load(body) or {}
    return Frontmatter.model_validate(raw)
