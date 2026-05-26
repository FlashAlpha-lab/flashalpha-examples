"""Loader + lookup for endpoint_tiers.yaml."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Literal

import yaml

Tier = Literal["free", "basic", "growth", "alpha"]
TIER_ORDER: tuple[Tier, ...] = ("free", "basic", "growth", "alpha")
_TIER_INDEX = {t: i for i, t in enumerate(TIER_ORDER)}


@dataclass(frozen=True)
class TierRule:
    prefix: str
    required: Tier


@dataclass(frozen=True)
class TierMap:
    rules: tuple[TierRule, ...]

    def required_for(self, path: str) -> Tier:
        """Return the tier required for `path`. First-match-wins."""
        for rule in self.rules:
            if path.startswith(rule.prefix):
                return rule.required
        raise KeyError(f"no tier rule matches path: {path!r}")


def load_tier_map(path: pathlib.Path) -> TierMap:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = tuple(
        TierRule(prefix=r["prefix"].strip(), required=r["required"].strip())
        for r in raw["rules"]
    )
    return TierMap(rules=rules)


def tier_covers(have: Tier, need: Tier) -> bool:
    """True if `have` is at least as high as `need`."""
    return _TIER_INDEX[have] >= _TIER_INDEX[need]
