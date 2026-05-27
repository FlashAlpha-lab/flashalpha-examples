"""Tests for sync_tier_map's parser of EndpointAccessMiddleware.cs."""

from __future__ import annotations

import textwrap

import pytest

from scripts.sync_tier_map import (
    AccessRule,
    parse_access_rules,
    rules_to_yaml,
    tier_for_set,
)


def test_tier_for_set_alpha_only():
    assert tier_for_set({"Business", "Institutional"}) == "alpha"


def test_tier_for_set_growth_set():
    assert tier_for_set({"ProPlus", "Business", "Institutional"}) == "growth"


def test_tier_for_set_basic_set():
    assert (
        tier_for_set({"Basic", "ProPlus", "Business", "Institutional"}) == "basic"
    )


def test_parse_access_rules_single_alpha_rule():
    source = textwrap.dedent("""\
        public class EndpointAccessMiddleware
        {
            private static readonly (string PathPrefix, HashSet<SubscriptionTier> AllowedTiers)[] AccessRules =
            [
                ("/v1/vrp/", AlphaAccess),
            ];
        }
    """)
    rules = parse_access_rules(source)
    assert rules == [AccessRule(prefix="/v1/vrp/", required="alpha")]


def test_parse_access_rules_ordered_specific_first():
    source = textwrap.dedent("""\
        AccessRules =
        [
            ("/v1/flow/levels/", GrowthAccess),
            ("/v1/flow/", AlphaAccess),
        ];
    """)
    rules = parse_access_rules(source)
    assert [r.prefix for r in rules] == ["/v1/flow/levels/", "/v1/flow/"]
    assert rules[0].required == "growth"
    assert rules[1].required == "alpha"


def test_parse_access_rules_skips_commented_lines():
    source = textwrap.dedent("""\
        AccessRules =
        [
            // ("/v1/disabled/", AlphaAccess),
            ("/v1/vrp/", AlphaAccess),
        ];
    """)
    rules = parse_access_rules(source)
    assert rules == [AccessRule(prefix="/v1/vrp/", required="alpha")]


def test_rules_to_yaml_emits_two_line_form():
    rules = [
        AccessRule(prefix="/v1/vrp/", required="alpha"),
        AccessRule(prefix="/v1/exposure/gex/", required="free"),
    ]
    out = rules_to_yaml(rules)
    assert "- prefix: /v1/vrp/" in out
    assert "  required: alpha" in out
    # No semicolon form
    assert "; required:" not in out
    # Header comment present
    assert "EndpointAccessMiddleware.cs" in out


def test_unknown_access_constant_raises():
    source = textwrap.dedent("""\
        AccessRules =
        [
            ("/v1/foo/", UnknownAccess),
        ];
    """)
    with pytest.raises(ValueError, match="UnknownAccess"):
        parse_access_rules(source)
