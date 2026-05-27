"""Parse EndpointAccessMiddleware.cs and regenerate endpoint_tiers.yaml.

The C# middleware is the single source of truth for which endpoints require
which subscription tier. This script extracts the ``AccessRules`` array and
emits a YAML mirror that Layer 4 tests against.

Usage (from repo root)::

    python -m scripts.sync_tier_map \\
        --middleware ../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs \\
        --out endpoint_tiers.yaml

If --middleware is omitted, the default path resolves relative to this repo::

    ../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys
from dataclasses import dataclass

# Map C# HashSet<SubscriptionTier> constants → canonical required tier.
# The required tier is the LOWEST tier in the set (the tier at which access
# is first granted). Defined in EndpointAccessMiddleware.cs lines 12-34.
_ACCESS_SETS = {
    "AlphaAccess": "alpha",    # {Business, Institutional}
    "GrowthAccess": "growth",  # {ProPlus, Business, Institutional}
    "BasicAccess": "basic",    # {Basic, ProPlus, Business, Institutional}
}

# Used by unit tests for tier_for_set
_TIER_TO_RANK = {
    "Starter": 0,
    "Basic": 1,
    "ProPlus": 2,
    "Business": 3,
    "Institutional": 4,
}
_RANK_TO_YAML = {0: "free", 1: "basic", 2: "growth", 3: "alpha", 4: "alpha"}


@dataclass(frozen=True)
class AccessRule:
    prefix: str
    required: str


def tier_for_set(tiers: set[str]) -> str:
    """Return the canonical YAML tier for a C# SubscriptionTier set.

    The required tier is the lowest-rank tier in the set.
    """
    if not tiers:
        raise ValueError("empty tier set")
    ranks = [_TIER_TO_RANK[t] for t in tiers]
    return _RANK_TO_YAML[min(ranks)]


# Regex matches `("/v1/something/", ConstantName),` lines inside AccessRules =
# [...]; the parser scans the whole source for these.
_RULE_RE = re.compile(
    r'^\s*\("(?P<prefix>/[^"]+)",\s*(?P<access>[A-Za-z]+)\)\s*,?\s*$',
    re.MULTILINE,
)
_COMMENT_RE = re.compile(r"^\s*//")


def parse_access_rules(source: str) -> list[AccessRule]:
    """Extract (prefix, required-tier) tuples from EndpointAccessMiddleware.cs.

    Skips C#-style ``//`` line comments. Order is preserved (first-match-wins
    semantics matter).
    """
    rules: list[AccessRule] = []
    for line in source.splitlines():
        if _COMMENT_RE.match(line):
            continue
        m = _RULE_RE.match(line)
        if not m:
            continue
        prefix = m.group("prefix")
        access = m.group("access")
        if access not in _ACCESS_SETS:
            raise ValueError(
                f"unknown access constant {access!r} for prefix {prefix!r}"
            )
        rules.append(AccessRule(prefix=prefix, required=_ACCESS_SETS[access]))
    return rules


# The catch-all free-tier prefixes that the middleware doesn't list explicitly
# (the middleware grants access by default to anything not matched by an
# AccessRules prefix). We must append these so Layer 4 has total coverage.
_DEFAULT_FREE_PREFIXES = [
    "/v1/exposure/gex/",
    "/v1/exposure/levels/",
    "/stockquote/",
    "/v1/summary/",
    "/v1/",  # final catch-all
]


def rules_to_yaml(rules: list[AccessRule]) -> str:
    """Render the rule list as a two-line-mapping YAML file."""
    today = dt.date.today().isoformat()
    lines = [
        f"# Generated {today} by scripts/sync_tier_map.py from",
        "# FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs.",
        "# DO NOT EDIT BY HAND — re-run the script to refresh.",
        "# Rules are ordered most-specific first; first prefix match wins.",
        "tiers: [free, basic, growth, alpha]",
        "rules:",
    ]
    for r in rules:
        lines.append(f"  - prefix: {r.prefix}")
        lines.append(f"    required: {r.required}")
    # Append default free-tier catch-alls (not explicit in middleware).
    lines.append(
        "  # Catch-all free-tier endpoints (anything not matched above is free)."
    )
    for prefix in _DEFAULT_FREE_PREFIXES:
        lines.append(f"  - prefix: {prefix}")
        lines.append("    required: free")
    return "\n".join(lines) + "\n"


def default_middleware_path() -> pathlib.Path:
    """Path to EndpointAccessMiddleware.cs relative to this repo."""
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    return (
        repo_root.parent.parent
        / "flashalpha-api"
        / "FlashAlpha.Api"
        / "Middleware"
        / "EndpointAccessMiddleware.cs"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--middleware",
        type=pathlib.Path,
        default=default_middleware_path(),
        help="Path to EndpointAccessMiddleware.cs",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=pathlib.Path("endpoint_tiers.yaml"),
        help="Output YAML path",
    )
    args = parser.parse_args(argv)
    if not args.middleware.exists():
        print(f"middleware source not found: {args.middleware}", file=sys.stderr)
        return 2
    source = args.middleware.read_text(encoding="utf-8")
    rules = parse_access_rules(source)
    yaml_text = rules_to_yaml(rules)
    args.out.write_text(yaml_text, encoding="utf-8")
    print(f"wrote {args.out} ({len(rules)} rules)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
