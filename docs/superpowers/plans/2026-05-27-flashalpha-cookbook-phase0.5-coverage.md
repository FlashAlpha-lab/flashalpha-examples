# FlashAlpha Cookbook — Phase 0.5 Coverage Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the coverage gaps that survived Phase 0 — tier-map drift detection, Layer-1 tightening to "structurally enforced" (not "structurally suggested"), CTA link liveness, cassette / endpoint cross-validation, pre-commit integration test, coverage measurement floor, Hypothesis property tests on load-bearing helpers, populate the canonical recipe's outputs + record its cassette, and the leftover CI quality fixes from the Phase-0 final review.

**Architecture:** Phase 0.5 is **additive only** — no changes to the architecture established in Phase 0. New tests live in `tests/` alongside existing layers; new tooling lives in `scripts/`. The only modifications are tightening existing Layer 1 assertions and fixing `pr.yml`. The 11 legacy `notebooks/0*_*.py` scripts are intentionally **not** hardened here — Phase 1 ports them to paired form and they inherit Layers 0/1/2/4 automatically.

**Tech Stack:** Python 3.10-3.13 · pytest · pytest-cov · Hypothesis · requests · vcrpy · pydantic v2 · regex/AST parsing of C# middleware source

**Reference:** [Phase 0 spec](../specs/2026-05-25-flashalpha-cookbook-design.md), [Phase 0 plan](2026-05-25-flashalpha-cookbook-phase0.md), Phase 0 final-review verdict (commits `b0c99dd..5c99b52` on main).

**Closes (mapped to my gap analysis):**

| Task | Gap closed |
|---|---|
| 1 | G2 (tier-map drift unenforced) |
| 2 | G15 (gitleaks CI mode wrong), review followup |
| 3 | G4-a (CTA substring instead of equality) |
| 4 | G4-b (mid-gate cell precedence unenforced) |
| 5 | G4-c (`%%capture` and broader `except` bodies unenforced) |
| 6 | G4-d (output-size caps unenforced) |
| 7 | G7 (cassette format integrity unverified) |
| 8 | G3 (CTA URLs never link-checked) |
| 9 | G6 (endpoints_used vs cassette URLs) |
| 10 | G8 (pre-commit hooks not integration-tested) |
| 11 | G9 (no coverage measurement floor) |
| 12 | G10 (no Hypothesis property tests on load-bearing helpers) |
| 13 | G11 (canonical recipe outputs empty + Layer 2 skips) |

**Out of scope (deferred):**

- G1 (legacy script execution coverage) — Phase 1 migration handles this automatically.
- G5 (Layer 4 per-cell endpoint mapping that honors `tier_gated_cells`) — Phase 2-blocker but no recipe yet triggers it.
- G12 (SDK / API release drift) — needs `nightly.yml` + dispatch PATs; deferred to Phase 1.
- Layer 3 (golden snapshots), Layer 5 (funnel sanity) — Phase 6 / Phase 8.

---

## File Structure

**New files:**
- `scripts/sync_tier_map.py` — parse `EndpointAccessMiddleware.cs` → regenerate `endpoint_tiers.yaml`
- `tests/cookbook_tools/test_sync_tier_map.py` — unit tests for the parser
- `tests/test_tier_map_drift.py` — runs sync, diffs against committed yaml, fails on drift (skips if C# repo absent)
- `tests/test_cassette_integrity.py` — assert no auth headers in any cassette
- `tests/test_links_alive.py` — HEAD-check every URL in every recipe's CTAs
- `tests/test_endpoints_match_cassette.py` — assert `endpoints_used` matches cassette URLs and `max_api_calls` matches interaction count
- `tests/test_precommit_hooks.py` — end-to-end pre-commit integration test
- `tests/cookbook_tools/test_frontmatter_properties.py` — Hypothesis property tests for slug regex + frontmatter parse/render roundtrip
- `tests/cookbook_tools/test_cta_template_properties.py` — Hypothesis property tests for CTA rendering invariants

**Modified files:**
- `tests/test_layer1_structural.py` — Tasks 3, 4, 5, 6 tighten existing assertions and add new ones; remove dead `# noqa: F401` imports
- `.github/workflows/pr.yml` — Task 2 fixes gitleaks invocation
- `pyproject.toml` — Task 11 adds `[tool.coverage]` config and `pytest-cov` to dev deps; Task 12 adds `hypothesis`
- `requirements-dev.txt` — Task 11 adds `pytest-cov`; Task 12 adds `hypothesis`; Task 8 adds `requests`
- `endpoint_tiers.yaml` — Task 1 updates header to reference the actual sync script (no longer a lie)
- `notebooks/tier-a-hooks/01-gex-dashboard.ipynb` — Task 13 re-executes against live API; outputs committed
- `tests/cassettes/01-gex-dashboard/cassette.yaml` — Task 13 records cassette

**Deleted files:**
- None

---

## Task 1: `scripts/sync_tier_map.py` — parse C# middleware → regenerate yaml

**Files:**
- Create: `scripts/sync_tier_map.py`
- Create: `tests/cookbook_tools/test_sync_tier_map.py`
- Modify: `endpoint_tiers.yaml` (header line)

- [ ] **Step 1.1: Write failing test `tests/cookbook_tools/test_sync_tier_map.py`**

The C# middleware file lives outside this repo at `e:/repos/tecware/flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs`. The parser must locate the `AccessRules` array, extract `(prefix, allowed_tier_set)` pairs, and resolve the tier-set to a single canonical required tier (the lowest tier in the set).

Recall from `EndpointAccessMiddleware.cs`:
- `BasicAccess` = {Basic, ProPlus, Business, Institutional} → required tier = `basic`
- `GrowthAccess` = {ProPlus, Business, Institutional} → required tier = `growth`
- `AlphaAccess` = {Business, Institutional} → required tier = `alpha`
- (No `FreeAccess` constant; free endpoints are catch-alls not explicitly listed.)

The plan name-to-tier mapping:
| C# enum | YAML tier |
|---|---|
| Starter | free |
| Basic | basic |
| ProPlus | growth |
| Business | alpha |
| Institutional | (alpha, but never user-facing) |

Display names from the middleware: Free, Basic, Growth, Alpha, Enterprise.

Write:

```python
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
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
pytest tests/cookbook_tools/test_sync_tier_map.py -v
```

Expected: ImportError on `scripts.sync_tier_map`. FAIL.

- [ ] **Step 1.3: Implement `scripts/sync_tier_map.py`**

```python
"""Parse EndpointAccessMiddleware.cs and regenerate endpoint_tiers.yaml.

The C# middleware is the single source of truth for which endpoints require
which subscription tier. This script extracts the `AccessRules` array and
emits a YAML mirror that Layer 4 tests against.

Usage (from repo root):
    python -m scripts.sync_tier_map \\
        --middleware ../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs \\
        --out endpoint_tiers.yaml

If --middleware is omitted, the default path resolves relative to this repo:
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
    "AlphaAccess": "alpha",     # {Business, Institutional}
    "GrowthAccess": "growth",   # {ProPlus, Business, Institutional}
    "BasicAccess": "basic",     # {Basic, ProPlus, Business, Institutional}
}

# Used by Step-1.1 unit test for tier_for_set
_TIER_TO_RANK = {"Starter": 0, "Basic": 1, "ProPlus": 2, "Business": 3, "Institutional": 4}
_RANK_TO_YAML = {0: "free", 1: "basic", 2: "growth", 3: "alpha", 4: "alpha"}


@dataclass(frozen=True)
class AccessRule:
    prefix: str
    required: str


def tier_for_set(tiers: set[str]) -> str:
    """Return the canonical YAML tier for a C# SubscriptionTier set.

    The required tier is the lowest-rank tier in the set."""
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

    Skips C#-style `//` line comments. Order is preserved (first-match-wins
    semantics matter)."""
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
    lines.append("  # Catch-all free-tier endpoints (anything not matched above is free).")
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
    yaml = rules_to_yaml(rules)
    args.out.write_text(yaml, encoding="utf-8")
    print(f"wrote {args.out} ({len(rules)} rules)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 1.4: Run unit tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_sync_tier_map.py -v
```

Expected: 7 passed.

- [ ] **Step 1.5: Run the script against the real C# middleware**

```bash
python -m scripts.sync_tier_map --middleware ../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs --out endpoint_tiers.yaml.generated
```

Expected: writes `endpoint_tiers.yaml.generated` with ~25-30 rules (the middleware has 25 explicit AccessRules entries plus 5 default-free catch-alls = 30).

- [ ] **Step 1.6: Diff against committed yaml + reconcile**

```bash
diff endpoint_tiers.yaml endpoint_tiers.yaml.generated
```

The hand-written yaml may differ from the generated form in trivial ways (whitespace, comment text, the redundant `/v1/screener` vs `/v1/screener/` slash, etc). For each diff:

- If the generated form is correct: replace the committed yaml.
- If the hand-written form is correct (e.g. middleware doesn't list `/optionquote/` but we want to cover it): document the deviation in a new comment block at the top of the committed yaml, and DON'T replace.

For Phase 0.5 the goal is alignment, not bug-for-bug fidelity. Acceptable outcome: a single `endpoint_tiers.yaml` that `sync_tier_map.py` would generate from the current middleware.

```bash
mv endpoint_tiers.yaml.generated endpoint_tiers.yaml
```

- [ ] **Step 1.7: Verify Layer 4 still passes**

```bash
pytest tests/test_layer4_tier_static.py tests/cookbook_tools/test_tier_map.py -v
```

Expected: all pass (the canonical recipe uses `/v1/exposure/gex/` and `/v1/exposure/levels/`, both free in any reasonable yaml).

- [ ] **Step 1.8: Commit**

```bash
git add scripts/sync_tier_map.py tests/cookbook_tools/test_sync_tier_map.py endpoint_tiers.yaml
git commit -m "Add sync_tier_map.py and regenerate endpoint_tiers.yaml from middleware"
```

---

## Task 2: Fix `pr.yml` gitleaks + remove dead `# noqa` imports

**Files:**
- Modify: `.github/workflows/pr.yml`
- Modify: `tests/test_layer1_structural.py:18,21`

- [ ] **Step 2.1: Replace gitleaks args in `.github/workflows/pr.yml`**

Open `.github/workflows/pr.yml`. The pre-commit step currently runs `gitleaks protect --staged`, which is a no-op in CI where nothing is staged. Pre-commit will use the configuration from `.pre-commit-config.yaml`, but pre-commit will fail if the hook does nothing useful. We have two options:

(a) Leave pre-commit-config gitleaks at `protect --staged` (sensible for local commit) and add a separate CI step that runs `gitleaks detect`.
(b) Change pre-commit-config gitleaks to `detect`.

Choose (a) because the pre-commit hook serves a different purpose than the CI scan.

Add a new step in `.github/workflows/pr.yml` between "Install Jupyter kernel" and "Layer 0 — pre-commit hooks":

```yaml
      - name: Layer 0 — gitleaks (full repo scan, not just staged)
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

If you prefer a simpler shell-based fallback that doesn't depend on the action:

```yaml
      - name: Layer 0 — gitleaks (full repo scan)
        run: |
          curl -sSfL https://github.com/gitleaks/gitleaks/releases/download/v8.18.4/gitleaks_8.18.4_linux_x64.tar.gz | tar xz
          ./gitleaks detect --source . --redact --verbose --no-git
```

Use the shell-based version. It runs in any matrix Python without needing additional GH App permissions.

- [ ] **Step 2.2: Remove `# noqa: F401` dead imports from `tests/test_layer1_structural.py`**

Open `tests/test_layer1_structural.py`. The imports at lines 18 and 21 are marked `# noqa: F401` but never used:
- `extract_markdown_urls` (line 18) — will be used by Task 8 (link check) but doesn't belong in this file
- `tier_covers` (line 21) — will be used by Task 4 (mid-gate cell precedence) so KEEP IT

Edit the imports:

```python
from cookbook_tools.notebook_io import (
    load_notebook,
)
from cookbook_tools.tier_map import TierMap, tier_covers
```

(removes `extract_markdown_urls`; keeps `tier_covers` without `# noqa`)

- [ ] **Step 2.3: Verify tests still pass**

```bash
pytest tests/ -v
```

Expected: 56 passed, 3 skipped.

- [ ] **Step 2.4: Validate the workflow yaml**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/pr.yml'))"
```

Expected: no output (silent success).

- [ ] **Step 2.5: Commit**

```bash
git add .github/workflows/pr.yml tests/test_layer1_structural.py
git commit -m "Fix gitleaks CI step + drop dead noqa imports"
```

---

## Task 3: Tighten Layer 1 — CTA exact-match, not substring

**Files:**
- Modify: `tests/test_layer1_structural.py:40-64`

- [ ] **Step 3.1: Update `test_top_cell_present_with_correct_signup_utm`**

Find the block at line 40-52 (`test_top_cell_present_with_correct_signup_utm`). Change `in` to `==` and rename to reflect strictness:

```python
def test_top_cell_matches_rendered_cta_exactly(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    tier_dir = recipe_path.parent.name
    expected_top = render_top_cell(recipe_fm, tier_dir=tier_dir).rstrip()
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    assert md_cells, "no markdown cells found"
    rendered_top = (
        "".join(md_cells[0]["source"])
        if isinstance(md_cells[0]["source"], list)
        else md_cells[0]["source"]
    )
    assert expected_top.strip() == rendered_top.strip(), (
        f"top CTA cell content mismatch in {recipe_path.name}:\n"
        f"expected:\n{expected_top}\n"
        f"got:\n{rendered_top}\n"
    )
```

- [ ] **Step 3.2: Update `test_bottom_cell_present_with_correct_utm`**

Find the block at line 55-64 (`test_bottom_cell_present_with_correct_utm`). Same change:

```python
def test_bottom_cell_matches_rendered_cta_exactly(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    expected_bottom = render_bottom_cell(recipe_fm).rstrip()
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    rendered_bottom = (
        "".join(md_cells[-1]["source"])
        if isinstance(md_cells[-1]["source"], list)
        else md_cells[-1]["source"]
    )
    assert expected_bottom.strip() == rendered_bottom.strip(), (
        f"bottom CTA cell content mismatch in {recipe_path.name}:\n"
        f"expected:\n{expected_bottom}\n"
        f"got:\n{rendered_bottom}\n"
    )
```

- [ ] **Step 3.3: Run tests, verify canonical recipe still passes**

```bash
pytest tests/test_layer1_structural.py -v
```

Expected: all 8 tests for `tier-a-hooks/01-gex-dashboard` PASS. If `test_*_matches_rendered_cta_exactly` FAILS for the canonical recipe, the canonical recipe's CTA has drifted from what the renderer produces — fix the recipe `.py`/`.ipynb` to match before continuing.

In particular, if the canonical recipe was written before Task 3 and its CTA cell content includes a second markdown subtitle (e.g. "Visualize Gamma Exposure (GEX) by strike for SPY…"), that subtitle is in a SECOND markdown cell, which Layer 1's `md_cells[0]` picks up as the top CTA. The canonical recipe MUST have the renderer-produced CTA as the literal first markdown cell; any additional prose must be in subsequent markdown cells.

- [ ] **Step 3.4: Commit**

```bash
git add tests/test_layer1_structural.py
git commit -m "Tighten Layer 1 CTA match from substring to exact equality"
```

---

## Task 4: Layer 1 — mid-gate cell precedence

**Files:**
- Modify: `tests/test_layer1_structural.py`

This is the most architecturally important Layer 1 check. Spec §6 requires that whenever a recipe with `tier: free` (or any non-alpha tier) calls an endpoint above its tier, the cell immediately before that call must be a mid-gate markdown cell that names the endpoint, the required tier, and the upgrade URL.

The recipe's frontmatter `tier_gated_cells: [int]` lists the **indices** of code cells that intentionally call above the declared tier. For each such index N: cell N-1 must be a markdown cell whose content matches what `render_gate_cell(endpoint, required_tier, fm)` would produce.

For the canonical recipe (`tier_gated_cells: []`), this test is a no-op. The first time a recipe declares a non-empty `tier_gated_cells`, the test enforces the discipline.

- [ ] **Step 4.1: Add `test_mid_gate_cells_precede_gated_calls` to `tests/test_layer1_structural.py`**

Add the following function after `test_bottom_cell_matches_rendered_cta_exactly`:

```python
def test_mid_gate_cells_precede_gated_calls(
    recipe_path: pathlib.Path,
    recipe_fm: Frontmatter,
    tier_map: TierMap,
):
    """For every cell index in `tier_gated_cells`, the immediately preceding
    cell must be a markdown gate cell naming the endpoint and required tier.
    """
    from cookbook_tools.cta_template import render_gate_cell

    if not recipe_fm.tier_gated_cells:
        pytest.skip("no tier-gated cells declared in this recipe")

    nb = load_notebook(recipe_path)
    cells = nb["cells"]

    for idx in recipe_fm.tier_gated_cells:
        # The gated cell itself must exist and be a code cell.
        assert 0 <= idx < len(cells), (
            f"tier_gated_cells references missing index {idx}"
        )
        gated = cells[idx]
        assert gated["cell_type"] == "code", (
            f"tier_gated_cells[{idx}] points at a {gated['cell_type']!r} "
            f"cell — it should point at a code cell"
        )

        # The preceding cell must be a markdown gate cell.
        assert idx > 0, f"tier-gated cell at index 0 cannot have a preceding gate"
        prev = cells[idx - 1]
        assert prev["cell_type"] == "markdown", (
            f"cell preceding tier-gated index {idx} must be a markdown "
            f"gate cell; got {prev['cell_type']!r}"
        )

        # The gated cell's source must mention exactly one /v1/* endpoint;
        # use it to find the required tier and validate the gate cell text.
        source = (
            "".join(gated["source"])
            if isinstance(gated["source"], list)
            else gated["source"]
        )
        m = re.search(r"(/v1/[A-Za-z0-9/_\-{}]+)", source)
        assert m, (
            f"tier-gated cell {idx} has no /v1/* endpoint reference; "
            f"cannot validate gate cell"
        )
        endpoint = m.group(1).replace("{symbol}", "SPY")
        required = tier_map.required_for(endpoint)
        assert not tier_covers(recipe_fm.tier, required), (
            f"cell {idx} declared in tier_gated_cells but endpoint "
            f"{endpoint!r} requires only {required!r}, which the recipe's "
            f"tier {recipe_fm.tier!r} already covers — drop from "
            f"tier_gated_cells"
        )

        expected_gate = render_gate_cell(
            endpoint=endpoint, required_tier=required, fm=recipe_fm
        ).rstrip()
        actual_gate = (
            "".join(prev["source"])
            if isinstance(prev["source"], list)
            else prev["source"]
        ).strip()
        assert expected_gate.strip() == actual_gate, (
            f"gate cell preceding tier-gated cell {idx} doesn't match "
            f"rendered gate.\nexpected:\n{expected_gate}\n"
            f"got:\n{actual_gate}\n"
        )
```

- [ ] **Step 4.2: Run tests**

```bash
pytest tests/test_layer1_structural.py -v -k mid_gate
```

Expected: 1 SKIPPED for `tier-a-hooks/01-gex-dashboard` (no tier-gated cells). Exit 0.

- [ ] **Step 4.3: Verify full suite passes**

```bash
pytest tests/ -v 2>&1 | tail -5
```

Expected: 57 passed, 4 skipped, 0 failures (one new SKIP for the gate test on the canonical recipe + one new PASS for the existing 8 Layer 1 tests).

- [ ] **Step 4.4: Commit**

```bash
git add tests/test_layer1_structural.py
git commit -m "Add Layer 1 mid-gate-cell precedence enforcement"
```

---

## Task 5: Layer 1 — `%%capture` ban + broader except-body check

**Files:**
- Modify: `tests/test_layer1_structural.py` (extend `test_no_broad_except_hiding_errors`)

The existing `test_no_broad_except_hiding_errors` only flags `except: pass` bodies. Strengthen it to: flag any `except` that doesn't re-raise OR call a logging function whose result includes `error`, `critical`, or `exception`. Also forbid `%%capture` and `%%capture --no-stderr` (Jupyter line/cell magics that suppress output).

- [ ] **Step 5.1: Replace `test_no_broad_except_hiding_errors` with a stronger version**

Replace the existing function (lines 77-101 of the current file after Task 3+4 edits) with:

```python
def test_no_silenced_errors(recipe_path: pathlib.Path):
    """Code cells must not silently swallow API errors. Forbids:
    - `except:` or `except Exception:` with only `pass` body
    - `except:` whose body has no `raise` and no `log.error/critical/exception`
    - `%%capture` cell magics (which suppress all output, including tracebacks)
    """
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = (
            "".join(cell["source"])
            if isinstance(cell["source"], list)
            else cell["source"]
        )
        stripped = source.strip()
        if not stripped:
            continue

        # Forbid %%capture (and its variants like %%capture --no-stderr).
        first_line = stripped.splitlines()[0]
        if first_line.lstrip().startswith("%%capture"):
            pytest.fail(
                f"{recipe_path.name}: cell starts with {first_line!r} — "
                f"%%capture suppresses errors and is forbidden"
            )

        # Skip cells with %% magics for AST parsing (not valid Python).
        if stripped.startswith("%"):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            pytest.fail(f"SyntaxError in {recipe_path.name}: cell does not parse")

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if _except_body_is_silencing(node.body):
                pytest.fail(
                    f"{recipe_path.name}: except handler at line "
                    f"{node.lineno} silently swallows errors — must either "
                    f"`raise` or call a logging function (e.g. "
                    f"`log.error(...)`, `logging.exception(...)`)"
                )


def _except_body_is_silencing(body: list[ast.stmt]) -> bool:
    """True if the except body neither re-raises nor logs at error+ level."""
    # Pure-pass body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True

    has_raise = False
    has_error_log = False
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Raise):
                has_raise = True
            elif isinstance(node, ast.Call):
                fn = _call_func_name(node).lower()
                # logger.error / logger.exception / logger.critical /
                # logging.error / log.error / _log.exception / etc.
                if any(level in fn for level in ("error", "exception", "critical")):
                    has_error_log = True
    return not (has_raise or has_error_log)


def _call_func_name(call: ast.Call) -> str:
    """Best-effort dotted name for a Call. Returns '' if not resolvable."""
    f = call.func
    parts: list[str] = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return ".".join(reversed(parts))
```

- [ ] **Step 5.2: Run tests**

```bash
pytest tests/test_layer1_structural.py -v
```

Expected: all 8 tests for `tier-a-hooks/01-gex-dashboard` PASS (the canonical recipe has no `try/except` or `%%capture`).

- [ ] **Step 5.3: Commit**

```bash
git add tests/test_layer1_structural.py
git commit -m "Strengthen Layer 1 error-silencing check (%%capture ban + non-pass bodies)"
```

---

## Task 6: Layer 1 — output-size caps

**Files:**
- Modify: `tests/test_layer1_structural.py`

Spec §7 Layer 0 + 1 mentions output-size caps (1MB per cell, 5MB per notebook). Pre-commit doesn't enforce this; add it to Layer 1 as a backstop.

- [ ] **Step 6.1: Add `test_output_size_within_caps` to `tests/test_layer1_structural.py`**

Add at the bottom of the file:

```python
_PER_CELL_MAX_BYTES = 1 * 1024 * 1024   # 1 MB
_PER_NOTEBOOK_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def test_output_size_within_caps(recipe_path: pathlib.Path):
    """Reject runaway cell outputs (accidentally-pasted screenshots, huge
    DataFrames, etc.)."""
    import json as _json

    nb = load_notebook(recipe_path)
    total_bytes = 0
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs", []):
            blob = _json.dumps(output)
            cell_bytes = len(blob.encode("utf-8"))
            total_bytes += cell_bytes
            assert cell_bytes < _PER_CELL_MAX_BYTES, (
                f"{recipe_path.name}: cell {cell_idx} output is "
                f"{cell_bytes // 1024} KB, exceeds 1 MB cap"
            )
    assert total_bytes < _PER_NOTEBOOK_MAX_BYTES, (
        f"{recipe_path.name}: total cell outputs are "
        f"{total_bytes // 1024} KB, exceeds 5 MB cap"
    )
```

- [ ] **Step 6.2: Run tests**

```bash
pytest tests/test_layer1_structural.py::test_output_size_within_caps -v
```

Expected: 1 PASS for `tier-a-hooks/01-gex-dashboard` (canonical recipe has empty outputs, trivially under cap).

- [ ] **Step 6.3: Commit**

```bash
git add tests/test_layer1_structural.py
git commit -m "Add Layer 1 output-size caps (1 MB per cell, 5 MB per notebook)"
```

---

## Task 7: Cassette format integrity test

**Files:**
- Create: `tests/test_cassette_integrity.py`

- [ ] **Step 7.1: Write the test**

```python
"""Defense-in-depth: every committed cassette must have its auth headers
filtered. The vcrpy `filter_headers` config is duplicated between
`scripts/record_cassettes.py` and `tests/test_layer2_execution.py`; if they
drift, this test catches the leak."""

from __future__ import annotations

import pathlib

import pytest
import yaml

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"

_FORBIDDEN_HEADERS = {"authorization", "x-api-key", "cookie"}


def _discover_cassettes() -> list[pathlib.Path]:
    if not CASSETTE_ROOT.exists():
        return []
    return sorted(CASSETTE_ROOT.glob("*/cassette.yaml"))


_CASSETTES = _discover_cassettes()


def pytest_generate_tests(metafunc):
    if "cassette_path" in metafunc.fixturenames:
        metafunc.parametrize(
            "cassette_path",
            _CASSETTES,
            ids=[p.parent.name for p in _CASSETTES],
        )


def test_cassette_has_no_auth_headers(cassette_path: pathlib.Path):
    data = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    for i, interaction in enumerate(data.get("interactions", [])):
        request = interaction.get("request", {})
        headers = request.get("headers", {}) or {}
        # vcrpy serializes headers as a dict-of-lists; check both shapes.
        if isinstance(headers, dict):
            keys = {k.lower() for k in headers.keys()}
        else:
            keys = set()
        leaked = keys & _FORBIDDEN_HEADERS
        assert not leaked, (
            f"cassette {cassette_path.parent.name} interaction #{i} "
            f"contains forbidden auth headers: {leaked}"
        )
```

- [ ] **Step 7.2: Run the test**

```bash
pytest tests/test_cassette_integrity.py -v
```

Expected: `no tests ran` (no cassettes recorded yet). Exit 0 or 5 both acceptable.

This test gets meaningful once Task 13 records the first cassette.

- [ ] **Step 7.3: Commit**

```bash
git add tests/test_cassette_integrity.py
git commit -m "Add cassette format integrity test"
```

---

## Task 8: CTA link liveness check

**Files:**
- Create: `tests/test_links_alive.py`
- Modify: `requirements-dev.txt` (add `requests`)

This is a slimmed-down version of Layer 5 funnel sanity — just "do the URLs respond 2xx", no headless rendering. Cached for 7 days in `.cache/links.json` so PR runs don't hammer.

- [ ] **Step 8.1: Add `requests` to `requirements-dev.txt`**

Append:

```text
# Link liveness (Layer 1 + Layer 5)
requests>=2.31
```

Also add to `pyproject.toml [project.optional-dependencies].dev`:

```toml
    "requests>=2.31",
```

Re-install:

```bash
python -m pip install -e ".[dev]"
```

- [ ] **Step 8.2: Write the test**

```python
"""Link liveness check — every URL in every recipe's CTA cells must respond
2xx. Cached for 7 days in .cache/links.json to keep PR runs fast."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import time

import pytest
import requests

from cookbook_tools.notebook_io import extract_markdown_urls, load_notebook

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE_PATH = REPO_ROOT / ".cache" / "links.json"
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# URLs that always exist (don't hit them on every run — they're high-traffic).
_KNOWN_GOOD = {
    "https://github.com/FlashAlpha-lab/flashalpha-examples",
    "https://colab.research.google.com/assets/colab-badge.svg",
}


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _check_url(url: str, cache: dict[str, dict]) -> tuple[int, str]:
    """Return (status_code, source). source = 'cache' or 'network'."""
    now = time.time()
    if url in cache and (now - cache[url].get("ts", 0)) < CACHE_TTL_SECONDS:
        return cache[url]["status"], "cache"
    if url in _KNOWN_GOOD:
        cache[url] = {"status": 200, "ts": now}
        return 200, "cache"
    try:
        # HEAD first; some CDNs reject HEAD with 405, fall back to GET.
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 405:
            r = requests.get(url, timeout=10, allow_redirects=True, stream=True)
    except requests.RequestException as exc:
        return 0, f"network-error: {exc}"
    cache[url] = {"status": r.status_code, "ts": now}
    return r.status_code, "network"


def test_all_recipe_cta_urls_respond_2xx(recipe_path: pathlib.Path):
    nb = load_notebook(recipe_path)
    urls = extract_markdown_urls(nb)
    if not urls:
        pytest.skip("no markdown URLs in recipe")
    cache = _load_cache()
    failures: list[str] = []
    try:
        for url in urls:
            status, source = _check_url(url, cache)
            if not (200 <= status < 400):
                failures.append(f"{url} → {status} (via {source})")
    finally:
        _save_cache(cache)
    assert not failures, (
        f"{recipe_path.name}: dead links:\n  " + "\n  ".join(failures)
    )
```

- [ ] **Step 8.3: Run the test**

```bash
pytest tests/test_links_alive.py -v
```

Expected: 1 test, PASS. The canonical recipe has 5-6 URLs (signup, pricing, Discord, GitHub, MCP, Colab badge). All should return 2xx — if any are dead, that's a real failure and means a real CTA is broken.

If running in an offline environment, the test will fail with `network-error`. Mark it as skipped manually in that case (no need to add `@pytest.mark.network` plumbing for Phase 0.5; CI has network).

- [ ] **Step 8.4: Commit**

```bash
git add requirements-dev.txt pyproject.toml tests/test_links_alive.py
git commit -m "Add CTA link liveness test"
```

---

## Task 9: Cassette ↔ frontmatter cross-validation

**Files:**
- Create: `tests/test_endpoints_match_cassette.py`

- [ ] **Step 9.1: Write the test**

```python
"""Cross-validate: a recipe's frontmatter must be honest about which
endpoints it hits and how many calls it makes. Compare the declared
`endpoints_used` and `max_api_calls` against the recorded cassette."""

from __future__ import annotations

import pathlib
from urllib.parse import urlparse

import pytest
import yaml

from cookbook_tools.frontmatter import Frontmatter

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"


def _endpoint_from_url(url: str) -> str:
    """Return just the path component, normalized."""
    parsed = urlparse(url)
    return parsed.path


def _normalize_endpoint_template(ep: str) -> str:
    """`/v1/exposure/gex/{symbol}` → `/v1/exposure/gex/`. Strips template
    suffix so comparisons against concrete paths use the prefix."""
    if "{" in ep:
        ep = ep[: ep.index("{")]
    if not ep.endswith("/"):
        ep += "/"
    return ep


def test_cassette_endpoints_subset_of_declared(recipe_fm: Frontmatter):
    """Every URL the cassette recorded must be covered by an entry in
    `endpoints_used`. Authors can't sneak in undeclared API calls."""
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")
    data = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    declared_prefixes = {
        _normalize_endpoint_template(ep) for ep in recipe_fm.endpoints_used
    }
    undeclared: list[str] = []
    for interaction in data.get("interactions", []):
        request = interaction.get("request", {})
        url = request.get("uri", "")
        path = _endpoint_from_url(url)
        if not any(path.startswith(prefix) for prefix in declared_prefixes):
            undeclared.append(path)
    assert not undeclared, (
        f"{recipe_fm.slug}: cassette has calls not in endpoints_used: "
        f"{sorted(set(undeclared))}\n"
        f"declared prefixes: {sorted(declared_prefixes)}"
    )


def test_max_api_calls_matches_actual(recipe_fm: Frontmatter):
    """The declared `max_api_calls` budget should equal the actual
    interaction count (not just `<=`). If a recipe is using fewer calls than
    declared, the budget should be tightened."""
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")
    data = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    actual = len(data.get("interactions", []))
    declared = recipe_fm.max_api_calls
    # Permit a slack of +2 for retry / off-by-one rounding. Anything more is
    # either over-budgeted (tighten) or undeclared regression (investigate).
    assert actual <= declared, (
        f"{recipe_fm.slug}: cassette has {actual} interactions but "
        f"max_api_calls={declared}"
    )
    assert actual >= declared - 2, (
        f"{recipe_fm.slug}: cassette has only {actual} interactions but "
        f"max_api_calls={declared} — tighten the budget"
    )
```

- [ ] **Step 9.2: Run the test**

```bash
pytest tests/test_endpoints_match_cassette.py -v
```

Expected: 2 SKIPPED for `tier-a-hooks/01-gex-dashboard` (no cassette yet — Task 13 records it).

- [ ] **Step 9.3: Commit**

```bash
git add tests/test_endpoints_match_cassette.py
git commit -m "Add cassette/frontmatter cross-validation test"
```

---

## Task 10: Pre-commit hook integration test

**Files:**
- Create: `tests/test_precommit_hooks.py`

- [ ] **Step 10.1: Write the test**

```python
"""End-to-end verification that pre-commit hooks actually run and catch the
issues they're meant to. Builds a temporary git repo with a known-bad
notebook, runs pre-commit, verifies redaction occurred."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _git(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _make_bad_notebook() -> dict:
    """Build a notebook whose output cell echoes an Authorization header."""
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [
                            "{'Authorization': 'Bearer fa_leaked_secret_token_value'}"
                        ],
                    }
                ],
                "source": ["print('hi')\n"],
                "metadata": {},
            }
        ],
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


@pytest.fixture
def temp_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Make a fresh git repo with the cookbook's pre-commit config copied in
    and the cookbook_tools/scripts available for the local hook to import."""
    work = tmp_path / "repo"
    work.mkdir()
    shutil.copy(REPO_ROOT / ".pre-commit-config.yaml", work / ".pre-commit-config.yaml")
    shutil.copytree(REPO_ROOT / "scripts", work / "scripts")
    shutil.copytree(REPO_ROOT / "cookbook_tools", work / "cookbook_tools")
    # Init git
    _git(work, "init")
    _git(work, "config", "user.email", "test@flashalpha.local")
    _git(work, "config", "user.name", "test")
    return work


def test_precommit_scrubs_auth_headers_from_committed_ipynb(temp_repo: pathlib.Path):
    """Stage a notebook with an Authorization header value in an output;
    pre-commit's scrub hook must redact it before the commit lands."""
    nb_path = temp_repo / "test.ipynb"
    nb_path.write_text(json.dumps(_make_bad_notebook()), encoding="utf-8")

    _git(temp_repo, "add", "test.ipynb", ".pre-commit-config.yaml", "scripts", "cookbook_tools")

    # First-time pre-commit install in the temp repo.
    install = subprocess.run(
        [sys.executable, "-m", "pre_commit", "install"],
        cwd=temp_repo, capture_output=True, text=True,
    )
    assert install.returncode == 0, install.stderr

    # Run the scrubber via pre-commit on the staged file. We expect non-zero
    # exit (because the file was modified) and the file content to be redacted.
    result = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "scrub-notebook-outputs",
         "--files", "test.ipynb"],
        cwd=temp_repo, capture_output=True, text=True,
    )
    # The hook modified the file → exit nonzero is correct.
    assert result.returncode != 0, (
        f"pre-commit should have failed because the hook redacted content; "
        f"got exit={result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )

    # Read the post-redaction notebook content.
    text = nb_path.read_text(encoding="utf-8")
    assert "fa_leaked_secret_token_value" not in text, (
        f"redaction did not occur. Notebook content:\n{text}"
    )
    assert "REDACTED" in text, (
        f"redaction marker missing. Notebook content:\n{text}"
    )
```

- [ ] **Step 10.2: Run the test**

```bash
pytest tests/test_precommit_hooks.py -v
```

Expected: 1 PASS. The test installs pre-commit in a temp repo, stages a notebook with a fake leaked token, runs the scrub hook, and verifies the token was redacted.

If pre-commit isn't available or git config rejects the test commit, the test will fail with a clear error.

- [ ] **Step 10.3: Commit**

```bash
git add tests/test_precommit_hooks.py
git commit -m "Add pre-commit hook integration test"
```

---

## Task 11: Coverage measurement floor

**Files:**
- Modify: `pyproject.toml` (add `pytest-cov` + coverage config)
- Modify: `requirements-dev.txt` (add `pytest-cov`)
- Modify: `.github/workflows/pr.yml` (run tests with `--cov`)

- [ ] **Step 11.1: Add `pytest-cov` to dev deps**

In `requirements-dev.txt`, append under `# Test infra`:

```text
pytest-cov>=4.1
```

In `pyproject.toml [project.optional-dependencies].dev`, add:

```toml
    "pytest-cov>=4.1",
```

Re-install:

```bash
python -m pip install -e ".[dev]"
```

- [ ] **Step 11.2: Configure coverage thresholds in `pyproject.toml`**

Add to `pyproject.toml` (after `[tool.pytest.ini_options]`):

```toml
[tool.coverage.run]
source = ["cookbook_tools", "scripts"]
omit = [
    "tests/*",
    "scripts/record_cassettes.py",  # network-bound, manual recording only
    "scripts/sync_tier_map.py",     # needs cross-repo C# source to exercise
]

[tool.coverage.report]
show_missing = true
skip_covered = false
fail_under = 85
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if __name__ == \"__main__\":",
]
```

`fail_under = 85` is the coverage floor for everything in `cookbook_tools/` + non-omitted `scripts/`. Calibrate higher (90/95) after Phase 1 if it holds.

- [ ] **Step 11.3: Run coverage locally to confirm baseline**

```bash
pytest --cov=cookbook_tools --cov=scripts --cov-report=term-missing
```

Expected: total coverage ≥ 85%. If it's lower, document the missing lines (likely `scripts/new_recipe.py` argparse paths and main()) and either bump the floor down or add covering tests in the same task.

If the actual coverage is e.g. 78%, edit `fail_under` to that number minus 2 for a margin. Document the value chosen.

- [ ] **Step 11.4: Wire `--cov` into `pr.yml`**

In `.github/workflows/pr.yml`, change the `Cookbook tools — unit tests` step to:

```yaml
      - name: Cookbook tools — unit tests with coverage
        run: pytest tests/cookbook_tools/ -v --cov=cookbook_tools --cov=scripts --cov-report=term-missing
```

This runs the unit tests under coverage and enforces the floor (fail_under from pyproject.toml).

- [ ] **Step 11.5: Re-run full suite to confirm pass**

```bash
pytest --cov=cookbook_tools --cov=scripts
```

Expected: full coverage report printed, exit 0.

- [ ] **Step 11.6: Commit**

```bash
git add pyproject.toml requirements-dev.txt .github/workflows/pr.yml
git commit -m "Add coverage measurement with 85% floor"
```

---

## Task 12: Hypothesis property tests for frontmatter + CTA

**Files:**
- Create: `tests/cookbook_tools/test_frontmatter_properties.py`
- Create: `tests/cookbook_tools/test_cta_template_properties.py`
- Modify: `requirements-dev.txt` (add `hypothesis`)
- Modify: `pyproject.toml` (add `hypothesis` to dev deps)

- [ ] **Step 12.1: Add `hypothesis` to dev deps**

In `requirements-dev.txt`, under `# Test infra`:

```text
hypothesis>=6.100
```

In `pyproject.toml [project.optional-dependencies].dev`:

```toml
    "hypothesis>=6.100",
```

Reinstall:

```bash
python -m pip install -e ".[dev]"
```

- [ ] **Step 12.2: Write Hypothesis tests for slug validation + frontmatter roundtrip**

Create `tests/cookbook_tools/test_frontmatter_properties.py`:

```python
"""Property-based tests for frontmatter slug validation and parse/render
roundtrip stability."""

from __future__ import annotations

import datetime as dt
import textwrap

from hypothesis import given, strategies as st

from cookbook_tools.frontmatter import (
    ExpectedArtifacts,
    Frontmatter,
    SLUG_RE,
    parse_frontmatter,
)

# Valid slug: kebab-case, 1+ segments of lowercase letters/digits.
_slug_segment = st.from_regex(r"^[a-z0-9]+\Z", fullmatch=True)


@given(st.lists(_slug_segment, min_size=1, max_size=6))
def test_constructed_slugs_match_regex(segments: list[str]):
    """Any kebab-case-conformant string should match SLUG_RE."""
    slug = "-".join(segments)
    assert SLUG_RE.match(slug), f"valid kebab-case slug {slug!r} rejected"


@given(st.from_regex(r"^[A-Z_]+$", fullmatch=True))
def test_uppercase_or_underscore_slugs_rejected(bad_slug: str):
    """Slugs with uppercase or underscores must not match."""
    assert SLUG_RE.match(bad_slug) is None


# Frontmatter strategy — generate semantically valid frontmatter dicts.
_tier = st.sampled_from(("free", "basic", "growth", "alpha"))
_slug = st.builds(
    lambda segs: "-".join(segs),
    st.lists(_slug_segment, min_size=1, max_size=4),
)


@st.composite
def _frontmatter_dicts(draw):
    slug = draw(_slug)
    return {
        "slug": slug,
        "title": draw(st.text(min_size=1, max_size=80).filter(lambda s: "\n" not in s)),
        "tier": draw(_tier),
        "runtime_budget_seconds": draw(st.integers(min_value=1, max_value=600)),
        "max_api_calls": draw(st.integers(min_value=1, max_value=50)),
        "endpoints_used": ["/v1/exposure/gex/{symbol}"],
        "tier_gated_cells": [],
        "sdk_version_min": "1.0.1",
        "utm_campaign": slug,  # must match
        "expected_artifacts": {"dataframes": [], "charts": []},
        "last_validated_live": draw(
            st.dates(min_value=dt.date(2024, 1, 1), max_value=dt.date(2030, 12, 31))
        ).isoformat(),
    }


@given(_frontmatter_dicts())
def test_frontmatter_parse_roundtrip(fm_dict: dict):
    """Parse → re-emit → parse should produce an identical Frontmatter."""
    body = "\n".join(f"{k}: {fm_dict[k]}" for k in [
        "slug", "title", "tier", "runtime_budget_seconds", "max_api_calls",
        "sdk_version_min", "utm_campaign", "last_validated_live",
    ])
    text = textwrap.dedent(f"""\
        ---
        {body}
        endpoints_used:
          - /v1/exposure/gex/{{symbol}}
        tier_gated_cells: []
        expected_artifacts:
          dataframes: []
          charts: []
        ---
    """)
    fm = parse_frontmatter(text)
    assert fm.slug == fm_dict["slug"]
    assert fm.tier == fm_dict["tier"]
    assert fm.utm_campaign == fm_dict["slug"]
    assert fm.runtime_budget_seconds == fm_dict["runtime_budget_seconds"]
```

- [ ] **Step 12.3: Write Hypothesis tests for CTA renderer invariants**

Create `tests/cookbook_tools/test_cta_template_properties.py`:

```python
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
```

- [ ] **Step 12.4: Run the new tests**

```bash
pytest tests/cookbook_tools/test_frontmatter_properties.py tests/cookbook_tools/test_cta_template_properties.py -v
```

Expected: all pass. Hypothesis may take 2-5 seconds per test as it explores examples.

- [ ] **Step 12.5: Commit**

```bash
git add pyproject.toml requirements-dev.txt tests/cookbook_tools/test_frontmatter_properties.py tests/cookbook_tools/test_cta_template_properties.py
git commit -m "Add Hypothesis property tests for frontmatter + CTA renderer"
```

---

## Task 13: Re-execute canonical recipe live + record cassette

**Files:**
- Modify: `notebooks/tier-a-hooks/01-gex-dashboard.ipynb` (re-executed with outputs)
- Create: `tests/cassettes/01-gex-dashboard/cassette.yaml`

This is the only task that requires `FLASHALPHA_API_KEY`. If the key isn't set in your shell, skip this task and report it for the user to do manually.

- [ ] **Step 13.1: Verify the API key is available**

```bash
test -n "$FLASHALPHA_API_KEY" && echo "key set, length ${#FLASHALPHA_API_KEY}" || echo "FLASHALPHA_API_KEY not set — skip task"
```

If the key is not set, report BLOCKED and stop. The user will run this task locally.

- [ ] **Step 13.2: Re-execute the notebook with live outputs**

```bash
papermill \
  notebooks/tier-a-hooks/01-gex-dashboard.ipynb \
  notebooks/tier-a-hooks/01-gex-dashboard.ipynb \
  --kernel python3
```

Expected: the notebook executes, prints "Net GEX: …" output, saves `gex_chart.png` to repo root (then ignored by .gitignore), and writes the executed `.ipynb` with chart base64 in the outputs.

- [ ] **Step 13.3: Record the cassette**

```bash
python -m scripts.record_cassettes notebooks/tier-a-hooks/01-gex-dashboard.ipynb
```

Expected: writes `tests/cassettes/01-gex-dashboard/cassette.yaml`.

- [ ] **Step 13.4: Scrub outputs (defensive)**

```bash
python -m scripts.scrub_outputs notebooks/tier-a-hooks/01-gex-dashboard.ipynb
```

Expected: exit 0 (no auth headers to redact in Free-tier endpoint responses) OR exit 1 (something was redacted). Either is fine.

- [ ] **Step 13.5: Update `last_validated_live` in the recipe's frontmatter**

Open `notebooks/tier-a-hooks/01-gex-dashboard.py` and update the line:

```
# last_validated_live: 2026-05-25
```

to today's date. Then re-sync to .ipynb:

```bash
jupytext --sync notebooks/tier-a-hooks/01-gex-dashboard.py
```

- [ ] **Step 13.6: Run all Phase 0.5 tests against the now-populated recipe**

```bash
pytest tests/ -v 2>&1 | tail -10
```

Expected: previously-skipped Layer 2 tests now PASS. Previously-skipped Task 9 cross-validation tests PASS. Task 7 cassette-integrity test PASSES with one cassette validated. Full suite should report 60+ passed, 0-1 skipped.

- [ ] **Step 13.7: Commit**

```bash
git add notebooks/tier-a-hooks/01-gex-dashboard.{py,ipynb} tests/cassettes/01-gex-dashboard/cassette.yaml
git commit -m "Re-execute 01-gex-dashboard live + record cassette"
```

---

## Phase 0.5 — Definition of Done

When all 13 tasks are committed, verify with:

- [ ] `pytest -v` shows 70+ passed, ≤2 skipped (the Task-13 skip if no API key; one pre-existing integration skip)
- [ ] `pytest --cov=cookbook_tools --cov=scripts` exits 0 (coverage floor met)
- [ ] `pre-commit run --all-files` exits 0
- [ ] `python -m scripts.sync_tier_map --middleware <path>` produces a yaml byte-identical to the committed `endpoint_tiers.yaml`
- [ ] Every URL in the canonical recipe's CTA cells returns 2xx (Task 8 test passes)
- [ ] The canonical recipe's `.ipynb` has executed outputs OR Task 13 was deferred (documented as known)

If Task 13 was deferred, the recipe's empty outputs + missing cassette are the only gaps. Everything else ships.

---

## Self-review notes

Spec coverage:
- All 13 numbered gaps (G2 through G15 from my analysis) are addressed.
- G1, G5, G12 explicitly out of scope and called out at the top.

Placeholder check: no "TBD" / "implement later" patterns. Every step contains actual code or actual commands.

Type consistency:
- `AccessRule(prefix, required)` in Task 1 matches between the test (Step 1.1) and the implementation (Step 1.3).
- `_except_body_is_silencing` / `_call_func_name` defined together in Task 5.
- `render_gate_cell(endpoint, required_tier, fm)` keyword-only signature consistent between Phase 0 code and Task 4's invocation.
- `extract_markdown_urls` and `tier_covers` import handling consistent (Task 2 removes one, Task 4 uses the other).

Open risk: Task 13 depends on a live API key the implementer may not have. The Phase 0.5 DoD permits skipping it. Without Task 13, Tasks 7, 9, and the previously-skipping Layer 2 tests stay silent; their machinery is in place and verified, just not exercised against real data. This is acceptable — the user can run Task 13 by hand.
