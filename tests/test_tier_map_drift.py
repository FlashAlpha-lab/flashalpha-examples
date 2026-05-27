"""Re-run sync_tier_map.py against the C# middleware and assert the
committed endpoint_tiers.yaml is byte-identical to what the script
produces. Catches drift without needing a nightly cron job.

Skips cleanly when the cross-repo middleware source isn't reachable
(CI without the flashalpha-api repo checked out — that's normal).
"""

from __future__ import annotations

import pathlib

import pytest

from scripts.sync_tier_map import default_middleware_path, parse_access_rules, rules_to_yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMITTED_YAML = REPO_ROOT / "endpoint_tiers.yaml"


def test_committed_yaml_matches_middleware_source():
    middleware = default_middleware_path()
    if not middleware.exists():
        pytest.skip(
            f"middleware source not reachable at {middleware} — skip in "
            f"environments without the flashalpha-api repo checked out"
        )

    source = middleware.read_text(encoding="utf-8")
    rules = parse_access_rules(source)
    expected = rules_to_yaml(rules)
    actual = COMMITTED_YAML.read_text(encoding="utf-8")

    # The header carries a date stamp that drifts day-to-day. Strip it
    # before comparing — the body is what matters for correctness.
    def _strip_date_header(text: str) -> str:
        lines = text.splitlines()
        # Drop any header lines that start with "# Generated YYYY-MM-DD"
        body_lines = [
            line for line in lines
            if not (line.startswith("# Generated ") and " by " in line)
        ]
        return "\n".join(body_lines)

    assert _strip_date_header(actual) == _strip_date_header(expected), (
        "endpoint_tiers.yaml has drifted from EndpointAccessMiddleware.cs.\n"
        "Run: python -m scripts.sync_tier_map\n"
        f"Then commit the regenerated endpoint_tiers.yaml.\n\n"
        f"First 200 chars of expected (from middleware):\n"
        f"{_strip_date_header(expected)[:200]}\n\n"
        f"First 200 chars of actual (committed):\n"
        f"{_strip_date_header(actual)[:200]}"
    )
