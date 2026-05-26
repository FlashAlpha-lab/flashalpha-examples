"""Pydantic schema for cookbook recipe frontmatter."""

from __future__ import annotations

import re
from datetime import date

import yaml
from pydantic import BaseModel, Field, model_validator

from .tier_map import Tier

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ExpectedArtifacts(BaseModel):
    dataframes: list[str] = Field(default_factory=list)
    charts: list[str] = Field(default_factory=list)


class Frontmatter(BaseModel):
    slug: str
    title: str
    tier: Tier
    runtime_budget_seconds: int = Field(gt=0)
    max_api_calls: int = Field(gt=0)
    endpoints_used: list[str]
    tier_gated_cells: list[int] = Field(default_factory=list)
    sdk_version_min: str
    utm_campaign: str
    expected_artifacts: ExpectedArtifacts = Field(default_factory=ExpectedArtifacts)
    last_validated_live: date

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
