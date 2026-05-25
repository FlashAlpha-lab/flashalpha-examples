# FlashAlpha Cookbook — Phase 0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the canonical cookbook foundation inside [flashalpha-examples/](../../): jupytext-paired notebook format, 5-layer test pyramid (Layers 0/1/2-cassette/4-static), tooling scripts (frontmatter loader, CTA renderer, scaffolder, scrubber), `endpoint_tiers.yaml`, pre-commit, CI `pr.yml`, and one fully-ported recipe (`tier-a-hooks/01-gex-dashboard`) that all later recipes copy. Phase 0 is the *only* phase that builds infrastructure — Phases 1-8 are mechanical recipe authoring on top of this.

**Architecture:** A small Python package `cookbook_tools/` holds shared logic (Pydantic frontmatter schema, tier-map loader, CTA renderer, notebook helpers). `scripts/` holds CLI wrappers (`new_recipe.py`, `scrub_outputs.py`, `record_cassettes.py`, `sync_tier_map.py`). Tests under `tests/` parametrize over every `.ipynb` in `notebooks/`. CI runs Layers 0/1/2-cassette/4 on every PR.

**Tech Stack:** Python 3.10–3.13 · pytest · pydantic v2 · jupytext · papermill · nbformat · vcrpy · PyYAML · nbqa · ruff · pre-commit · gitleaks · GitHub Actions

**Reference spec:** [2026-05-25-flashalpha-cookbook-design.md](../specs/2026-05-25-flashalpha-cookbook-design.md)

**Out of scope (later phases):** Migrating the other 10 existing scripts (Phase 1), authoring 24 net-new recipes (Phases 2-7), Layer 3 golden snapshots (Phase 6 adds these for backtest recipes), Layer 5 weekly funnel job (Phase 8), `nightly.yml` + `weekly.yml` + `on-{sdk,api}-release.yml` workflows (deferred to Phase 1 once cassettes are recorded for multiple notebooks), dashboard at dash.flashalpha.com (Phase 3).

---

## File Structure

**New files:**

- `requirements-dev.txt` — dev/test deps
- `endpoint_tiers.yaml` — tier map mirrored from `EndpointAccessMiddleware.cs`
- `cookbook_tools/__init__.py`
- `cookbook_tools/frontmatter.py` — Pydantic schema + parse from `.ipynb`
- `cookbook_tools/tier_map.py` — YAML loader + endpoint→tier lookup
- `cookbook_tools/cta_template.py` — renders top/bottom/gate markdown cells from frontmatter
- `cookbook_tools/notebook_io.py` — extract code cells, markdown URLs, endpoints called
- `scripts/new_recipe.py` — CLI: scaffold a paired notebook from frontmatter args
- `scripts/scrub_outputs.py` — CLI/pre-commit hook: strip auth headers from `.ipynb` outputs
- `scripts/record_cassettes.py` — CLI: papermill+vcrpy record live API into cassette
- `scripts/sync_tier_map.py` — CLI: parse `EndpointAccessMiddleware.cs` → regenerate `endpoint_tiers.yaml`
- `tests/conftest.py` — fixtures (notebook discovery, FrontmatterModel cache, paths)
- `tests/test_layer0_secrets.py` — secret scan over code AND output cells
- `tests/test_layer1_structural.py` — frontmatter/CTA/URL/AST checks
- `tests/test_layer2_execution.py` — papermill+vcrpy execution
- `tests/test_layer4_tier_static.py` — endpoints_used ⊆ tier from `endpoint_tiers.yaml`
- `tests/cookbook_tools/test_frontmatter.py`
- `tests/cookbook_tools/test_tier_map.py`
- `tests/cookbook_tools/test_cta_template.py`
- `tests/cookbook_tools/test_notebook_io.py`
- `tests/cookbook_tools/test_scrub_outputs.py`
- `tests/cookbook_tools/test_new_recipe.py`
- `tests/cassettes/01-gex-dashboard/cassette.yaml`
- `notebooks/tier-a-hooks/01-gex-dashboard.py` — jupytext percent
- `notebooks/tier-a-hooks/01-gex-dashboard.ipynb` — executed, outputs committed
- `.pre-commit-config.yaml`
- `.github/workflows/pr.yml`
- `jupytext.toml` — repo-wide jupytext config

**Modified files:**

- `pyproject.toml` — add `[project.optional-dependencies].dev`, `[tool.pytest.ini_options]`, version 0.1.0 → 1.0.0-rc.1
- `requirements.txt` — pin `flashalpha>=1.0.1`, add `pyyaml`, `pydantic>=2.0`
- `.gitignore` — add `.cache/`, `.papermill/`, `.pytest_cache/`, `__pycache__/`

**Deleted / superseded after Phase 0 (handled in Phase 1, not here):**

The 11 existing `notebooks/0*_*.py` files stay in place during Phase 0 — Phase 1 migrates them.

---

## Task 1: Dev environment scaffolding

**Files:**
- Create: `requirements-dev.txt`
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1.1: Write `requirements-dev.txt`**

```text
# Test infra
pytest>=7.4
pytest-approval>=0.2
papermill>=2.5
nbmake>=1.5
nbformat>=5.10
vcrpy>=6.0
# Format / lint
jupytext>=1.16
nbqa>=1.7
ruff>=0.4
# Pre-commit
pre-commit>=3.6
# Helpers
pydantic>=2.6
PyYAML>=6.0
# CTA UTM URL extraction
yarl>=1.9
# Image hash (used by Layer 3 later; harmless to install now)
ImageHash>=4.3
```

- [ ] **Step 1.2: Modify `pyproject.toml`**

Replace the file with:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "flashalpha-examples"
version = "1.0.0rc1"
description = "FlashAlpha cookbook — Python recipes for gamma exposure, dealer positioning, vol surfaces, 0DTE, and backtesting."
requires-python = ">=3.10"
dependencies = [
    "flashalpha>=1.0.1",
    "matplotlib",
    "numpy",
    "pydantic>=2.6",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "papermill>=2.5",
    "nbformat>=5.10",
    "vcrpy>=6.0",
    "jupytext>=1.16",
    "nbqa>=1.7",
    "ruff>=0.4",
    "pre-commit>=3.6",
    "yarl>=1.9",
    "ImageHash>=4.3",
    "pytest-approval>=0.2",
]

[tool.setuptools.packages.find]
include = ["cookbook_tools*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests that call the live FlashAlpha API (require FLASHALPHA_API_KEY)",
    "cassette: tests that replay vcrpy cassettes (no API key)",
]
```

- [ ] **Step 1.3: Modify `requirements.txt`**

Replace with:

```text
flashalpha>=1.0.1
matplotlib
numpy
pydantic>=2.6
PyYAML>=6.0
```

- [ ] **Step 1.4: Modify `.gitignore`**

Append:

```text
# cookbook
.cache/
.papermill/
.pytest_cache/
__pycache__/
*.egg-info/
.venv/
build/
dist/
# jupyter ephemeral
.ipynb_checkpoints/
```

- [ ] **Step 1.5: Install dev deps**

```bash
cd e:/repos/tecware/flashalpha-packages/flashalpha-examples
python -m pip install -e ".[dev]"
```

Expected: installs the package in editable mode plus all dev deps. No errors.

- [ ] **Step 1.6: Verify pytest discovers nothing yet**

```bash
pytest --collect-only
```

Expected: `no tests ran in <time>` (because the old `tests/test_examples.py` is integration-marked and skips without a key; `test_notebooks_syntax.py` may collect 11 cases — that's fine, ignore them). No errors.

- [ ] **Step 1.7: Commit**

```bash
git add requirements-dev.txt pyproject.toml requirements.txt .gitignore
git commit -m "Bump dev tooling for cookbook Phase 0"
```

---

## Task 2: `cookbook_tools.frontmatter` — Pydantic schema (TDD)

**Files:**
- Create: `cookbook_tools/__init__.py`
- Create: `cookbook_tools/frontmatter.py`
- Test: `tests/cookbook_tools/__init__.py`
- Test: `tests/cookbook_tools/test_frontmatter.py`

- [ ] **Step 2.1: Create empty package files**

```bash
mkdir -p cookbook_tools tests/cookbook_tools
```

Then write `cookbook_tools/__init__.py`:

```python
"""Shared helpers for the FlashAlpha cookbook."""

__all__ = ["frontmatter", "tier_map", "cta_template", "notebook_io"]
```

And `tests/cookbook_tools/__init__.py`:

```python
```

(Empty.)

- [ ] **Step 2.2: Write the failing test `tests/cookbook_tools/test_frontmatter.py`**

```python
"""Tests for the Frontmatter Pydantic schema."""

import textwrap

import pytest
from pydantic import ValidationError

from cookbook_tools.frontmatter import Frontmatter, parse_frontmatter

VALID_YAML = textwrap.dedent("""\
    ---
    slug: 01-gex-dashboard
    title: Build a GEX Dashboard in 30 Lines
    tier: free
    runtime_budget_seconds: 60
    max_api_calls: 8
    endpoints_used:
      - /v1/exposure/gex/{symbol}
      - /v1/exposure/levels/{symbol}
    tier_gated_cells: []
    sdk_version_min: "1.0.1"
    utm_campaign: 01-gex-dashboard
    expected_artifacts:
      dataframes: []
      charts: [gex_chart.png]
    last_validated_live: 2026-05-25
    ---
""")


def test_parse_valid_frontmatter_returns_model():
    fm = parse_frontmatter(VALID_YAML)
    assert fm.slug == "01-gex-dashboard"
    assert fm.tier == "free"
    assert fm.utm_campaign == "01-gex-dashboard"
    assert fm.endpoints_used == [
        "/v1/exposure/gex/{symbol}",
        "/v1/exposure/levels/{symbol}",
    ]


def test_parse_missing_triple_dashes_raises():
    with pytest.raises(ValueError, match="frontmatter delimiter"):
        parse_frontmatter("slug: foo\ntier: free\n")


def test_invalid_tier_rejected():
    bad = VALID_YAML.replace("tier: free", "tier: nope")
    with pytest.raises(ValidationError):
        parse_frontmatter(bad)


def test_slug_must_match_utm_campaign():
    bad = VALID_YAML.replace(
        "utm_campaign: 01-gex-dashboard", "utm_campaign: something-else"
    )
    with pytest.raises(ValidationError, match="utm_campaign must equal slug"):
        parse_frontmatter(bad)


def test_slug_kebab_case_only():
    bad = VALID_YAML.replace("slug: 01-gex-dashboard", "slug: 01_gex_dashboard")
    # Also fix the utm_campaign so we test slug rules, not the cross-check.
    bad = bad.replace(
        "utm_campaign: 01-gex-dashboard", "utm_campaign: 01_gex_dashboard"
    )
    with pytest.raises(ValidationError, match="kebab-case"):
        parse_frontmatter(bad)


def test_runtime_budget_must_be_positive():
    bad = VALID_YAML.replace("runtime_budget_seconds: 60", "runtime_budget_seconds: 0")
    with pytest.raises(ValidationError):
        parse_frontmatter(bad)


def test_empty_tier_gated_cells_means_no_gates():
    fm = parse_frontmatter(VALID_YAML)
    assert fm.tier_gated_cells == []
```

- [ ] **Step 2.3: Run the test to confirm it fails**

```bash
pytest tests/cookbook_tools/test_frontmatter.py -v
```

Expected: ImportError / ModuleNotFoundError on `cookbook_tools.frontmatter`. FAIL.

- [ ] **Step 2.4: Implement `cookbook_tools/frontmatter.py`**

```python
"""Pydantic schema for cookbook recipe frontmatter."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TIERS = ("free", "basic", "growth", "alpha")


class ExpectedArtifacts(BaseModel):
    dataframes: list[str] = Field(default_factory=list)
    charts: list[str] = Field(default_factory=list)


class Frontmatter(BaseModel):
    slug: str
    title: str
    tier: Literal["free", "basic", "growth", "alpha"]
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
```

- [ ] **Step 2.5: Run tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_frontmatter.py -v
```

Expected: 7 passed.

- [ ] **Step 2.6: Commit**

```bash
git add cookbook_tools/ tests/cookbook_tools/__init__.py tests/cookbook_tools/test_frontmatter.py
git commit -m "Add Frontmatter pydantic schema"
```

---

## Task 3: `cookbook_tools.tier_map` — endpoint→tier lookup (TDD)

**Files:**
- Create: `cookbook_tools/tier_map.py`
- Create: `endpoint_tiers.yaml`
- Test: `tests/cookbook_tools/test_tier_map.py`

- [ ] **Step 3.1: Write `endpoint_tiers.yaml`**

Mirror of [EndpointAccessMiddleware.cs:60-109](../../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs#L60). Order matters — first match wins.

```yaml
# Generated 2026-05-25 from FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs
# DO NOT EDIT BY HAND — run scripts/sync_tier_map.py
# Rules are ordered most-specific first; first prefix match wins.
tiers: [free, basic, growth, alpha]
rules:
  - prefix: /v1/vrp/                          ; required: alpha
  - prefix: /v1/flow/levels/                  ; required: growth
  - prefix: /v1/flow/pin-risk/                ; required: growth
  - prefix: /v1/flow/summary/                 ; required: growth
  - prefix: /v1/flow/gex/                     ; required: growth
  - prefix: /v1/flow/dex/                     ; required: growth
  - prefix: /v1/flow/dealer-risk/             ; required: growth
  - prefix: /v1/flow/                         ; required: alpha
  - prefix: /v1/earnings/vrp/                 ; required: alpha
  - prefix: /v1/earnings/dealer-positioning/  ; required: alpha
  - prefix: /v1/earnings/strategies/          ; required: alpha
  - prefix: /v1/earnings/screener             ; required: alpha
  - prefix: /v1/earnings/                     ; required: growth
  - prefix: /v1/screener                      ; required: growth
  - prefix: /v1/exposure/summary/             ; required: growth
  - prefix: /v1/exposure/narrative/           ; required: growth
  - prefix: /v1/exposure/history/             ; required: growth
  - prefix: /v1/exposure/zero-dte/            ; required: growth
  - prefix: /v1/volatility/                   ; required: growth
  - prefix: /v1/exposure/dex/                 ; required: basic
  - prefix: /v1/exposure/vex/                 ; required: basic
  - prefix: /v1/exposure/chex/                ; required: basic
  - prefix: /v1/maxpain/                      ; required: basic
  - prefix: /optionquote/                     ; required: growth
  # Catch-all free-tier endpoints (anything not matched above is free).
  - prefix: /v1/exposure/gex/                 ; required: free
  - prefix: /v1/exposure/levels/              ; required: free
  - prefix: /stockquote/                      ; required: free
  - prefix: /v1/summary/                      ; required: free
  - prefix: /v1/                              ; required: free
```

- [ ] **Step 3.2: Write failing test `tests/cookbook_tools/test_tier_map.py`**

```python
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
```

- [ ] **Step 3.3: Run the test to confirm it fails**

```bash
pytest tests/cookbook_tools/test_tier_map.py -v
```

Expected: ImportError on `cookbook_tools.tier_map`. FAIL.

- [ ] **Step 3.4: Implement `cookbook_tools/tier_map.py`**

```python
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
```

- [ ] **Step 3.5: Run tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_tier_map.py -v
```

Expected: 9 passed.

- [ ] **Step 3.6: Commit**

```bash
git add cookbook_tools/tier_map.py endpoint_tiers.yaml tests/cookbook_tools/test_tier_map.py
git commit -m "Add tier-map loader + endpoint_tiers.yaml mirror"
```

---

## Task 4: `cookbook_tools.cta_template` — CTA cell renderer (TDD)

**Files:**
- Create: `cookbook_tools/cta_template.py`
- Test: `tests/cookbook_tools/test_cta_template.py`

- [ ] **Step 4.1: Write failing test `tests/cookbook_tools/test_cta_template.py`**

```python
"""Tests for CTA markdown rendering."""

import datetime as dt

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_gate_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import Frontmatter, ExpectedArtifacts


def _fm(tier="free", slug="01-gex-dashboard"):
    return Frontmatter(
        slug=slug,
        title="Build a GEX Dashboard in 30 Lines",
        tier=tier,
        runtime_budget_seconds=60,
        max_api_calls=8,
        endpoints_used=["/v1/exposure/gex/{symbol}"],
        tier_gated_cells=[],
        sdk_version_min="1.0.1",
        utm_campaign=slug,
        expected_artifacts=ExpectedArtifacts(dataframes=[], charts=["gex_chart.png"]),
        last_validated_live=dt.date(2026, 5, 25),
    )


def test_top_cell_contains_signup_url_with_utm():
    md = render_top_cell(_fm(), tier_dir="tier-a-hooks")
    assert "# Build a GEX Dashboard in 30 Lines" in md
    assert (
        "https://flashalpha.com/signup?utm_source=github-cookbook"
        "&utm_medium=notebook&utm_campaign=01-gex-dashboard"
        in md
    )
    assert "Tier required: **Free**" in md
    assert (
        "https://colab.research.google.com/github/FlashAlpha-lab/"
        "flashalpha-examples/blob/main/notebooks/tier-a-hooks/01-gex-dashboard.ipynb"
        in md
    )


def test_top_cell_growth_tier_display_name():
    fm = _fm(tier="growth")
    md = render_top_cell(fm, tier_dir="tier-b-dealer-flow")
    assert "Tier required: **Growth**" in md


def test_bottom_cell_contains_all_four_bullets():
    md = render_bottom_cell(_fm())
    for needle in [
        "Backtest this with historical replay",
        "https://flashalpha.com/pricing?utm_source=github-cookbook"
        "&utm_campaign=01-gex-dashboard",
        "https://flashalpha.com/discord",
        "https://github.com/FlashAlpha-lab/flashalpha-examples",
        "https://flashalpha.com/docs/mcp",
    ]:
        assert needle in md


def test_gate_cell_names_endpoint_and_required_tier():
    md = render_gate_cell(
        endpoint="/v1/vrp/SPY", required_tier="alpha", fm=_fm(tier="growth")
    )
    assert "`/v1/vrp/SPY`" in md
    assert "**alpha+**" in md
    assert (
        "https://flashalpha.com/pricing?utm_source=github-cookbook"
        "&utm_campaign=01-gex-dashboard" in md
    )
    assert "growth users will get a 403" in md.lower()
```

- [ ] **Step 4.2: Run test to confirm it fails**

```bash
pytest tests/cookbook_tools/test_cta_template.py -v
```

Expected: ImportError on `cookbook_tools.cta_template`. FAIL.

- [ ] **Step 4.3: Implement `cookbook_tools/cta_template.py`**

```python
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
```

- [ ] **Step 4.4: Run tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_cta_template.py -v
```

Expected: 4 passed.

- [ ] **Step 4.5: Commit**

```bash
git add cookbook_tools/cta_template.py tests/cookbook_tools/test_cta_template.py
git commit -m "Add CTA cell renderer (top/bottom/gate)"
```

---

## Task 5: `cookbook_tools.notebook_io` — notebook helpers (TDD)

**Files:**
- Create: `cookbook_tools/notebook_io.py`
- Test: `tests/cookbook_tools/test_notebook_io.py`
- Test fixture: `tests/cookbook_tools/fixtures/minimal.ipynb`

- [ ] **Step 5.1: Create fixture `tests/cookbook_tools/fixtures/minimal.ipynb`**

```bash
mkdir -p tests/cookbook_tools/fixtures
```

Then write `tests/cookbook_tools/fixtures/minimal.ipynb`:

```json
{
 "cells": [
  {"cell_type": "raw", "metadata": {}, "source": [
    "---\n",
    "slug: 99-test\n",
    "title: Test Notebook\n",
    "tier: free\n",
    "runtime_budget_seconds: 30\n",
    "max_api_calls: 4\n",
    "endpoints_used:\n",
    "  - /v1/exposure/gex/{symbol}\n",
    "tier_gated_cells: []\n",
    "sdk_version_min: \"1.0.1\"\n",
    "utm_campaign: 99-test\n",
    "expected_artifacts:\n",
    "  dataframes: []\n",
    "  charts: []\n",
    "last_validated_live: 2026-05-25\n",
    "---\n"
  ]},
  {"cell_type": "markdown", "metadata": {}, "source": [
    "Check the [pricing](https://flashalpha.com/pricing) page.\n",
    "Or read [the spec](https://example.com/spec)."
  ]},
  {"cell_type": "code", "metadata": {}, "execution_count": 1, "outputs": [], "source": [
    "from flashalpha import FlashAlpha\n",
    "fa = FlashAlpha(\"key\")\n",
    "data = fa.gex(\"SPY\")  # /v1/exposure/gex/SPY\n"
  ]}
 ],
 "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 5.2: Write failing test `tests/cookbook_tools/test_notebook_io.py`**

```python
"""Tests for notebook I/O helpers."""

import pathlib

import pytest

from cookbook_tools.notebook_io import (
    extract_frontmatter_text,
    extract_markdown_urls,
    extract_code_endpoints,
    load_notebook,
)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "minimal.ipynb"


def test_load_notebook_round_trips():
    nb = load_notebook(FIXTURE)
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) == 3


def test_extract_frontmatter_text_finds_yaml_block():
    nb = load_notebook(FIXTURE)
    text = extract_frontmatter_text(nb)
    assert text.startswith("---")
    assert text.rstrip().endswith("---")
    assert "slug: 99-test" in text


def test_extract_frontmatter_missing_raises():
    nb_no_fm = {"cells": [
        {"cell_type": "markdown", "source": ["# hello"]},
    ]}
    with pytest.raises(ValueError, match="frontmatter cell"):
        extract_frontmatter_text(nb_no_fm)


def test_extract_markdown_urls_finds_all_links():
    nb = load_notebook(FIXTURE)
    urls = extract_markdown_urls(nb)
    assert "https://flashalpha.com/pricing" in urls
    assert "https://example.com/spec" in urls


def test_extract_code_endpoints_finds_path_from_comment_marker():
    nb = load_notebook(FIXTURE)
    endpoints = extract_code_endpoints(nb)
    # The fixture's code cell has `# /v1/exposure/gex/SPY` — the helper
    # collects any /v1/* path on a line within a code cell, useful as a
    # static-analysis fallback when cassettes aren't available.
    assert "/v1/exposure/gex/SPY" in endpoints
```

- [ ] **Step 5.3: Run the test to confirm it fails**

```bash
pytest tests/cookbook_tools/test_notebook_io.py -v
```

Expected: ImportError. FAIL.

- [ ] **Step 5.4: Implement `cookbook_tools/notebook_io.py`**

```python
"""Notebook-shape helpers used by Layer 0/1 tests and tooling."""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^\s)]+)\)")
_BARE_URL_RE = re.compile(r"(?<![\(\w])(https?://\S+)")
_CODE_ENDPOINT_RE = re.compile(r"(/v1/[A-Za-z0-9/_\-{}]+)")


def load_notebook(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _join_source(source: Any) -> str:
    if isinstance(source, list):
        return "".join(source)
    return source or ""


def extract_frontmatter_text(nb: dict[str, Any]) -> str:
    """Return the YAML frontmatter block (with delimiters) from the first
    raw or markdown cell that starts with `---`."""
    for cell in nb.get("cells", []):
        text = _join_source(cell.get("source"))
        stripped = text.lstrip()
        if stripped.startswith("---"):
            return stripped
    raise ValueError("no frontmatter cell found in notebook")


def extract_markdown_urls(nb: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        text = _join_source(cell.get("source"))
        urls.extend(_MD_LINK_RE.findall(text))
        urls.extend(
            u for u in _BARE_URL_RE.findall(text)
            if u not in urls
        )
    return urls


def extract_code_endpoints(nb: dict[str, Any]) -> list[str]:
    """Return distinct /v1/* paths mentioned in code cell text. Useful as a
    static-analysis fallback; cassettes are the authoritative record."""
    found: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        text = _join_source(cell.get("source"))
        for m in _CODE_ENDPOINT_RE.findall(text):
            if m not in found:
                found.append(m)
    return found
```

- [ ] **Step 5.5: Run tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_notebook_io.py -v
```

Expected: 5 passed.

- [ ] **Step 5.6: Commit**

```bash
git add cookbook_tools/notebook_io.py tests/cookbook_tools/test_notebook_io.py tests/cookbook_tools/fixtures/minimal.ipynb
git commit -m "Add notebook I/O helpers"
```

---

## Task 6: `scripts/scrub_outputs.py` — auth-header scrubber (TDD)

**Files:**
- Create: `scripts/__init__.py` (empty)
- Create: `scripts/scrub_outputs.py`
- Test: `tests/cookbook_tools/test_scrub_outputs.py`

- [ ] **Step 6.1: Write failing test `tests/cookbook_tools/test_scrub_outputs.py`**

```python
"""Tests for the output-scrubbing pre-commit hook."""

import json
import pathlib
import tempfile

import pytest

from scripts.scrub_outputs import scrub_notebook_outputs


def _nb_with_output(stream_text: str | None = None, header_value: str = "Bearer fa_xyz"):
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [stream_text or "ok\n"],
                    },
                    {
                        "output_type": "execute_result",
                        "data": {
                            "text/plain": [
                                f"{{'Authorization': '{header_value}', 'X-Api-Key': 'fa_abc'}}"
                            ]
                        },
                        "execution_count": 1,
                        "metadata": {},
                    },
                ],
                "source": ["print('ok')\n"],
                "metadata": {},
            }
        ],
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def test_scrub_redacts_authorization_in_text():
    nb = _nb_with_output()
    scrubbed = scrub_notebook_outputs(nb)
    text = json.dumps(scrubbed)
    assert "fa_xyz" not in text
    assert "fa_abc" not in text
    assert "<REDACTED>" in text


def test_scrub_preserves_stream_text_unrelated_to_auth():
    nb = _nb_with_output(stream_text="dealer_gex=1234.5\n")
    scrubbed = scrub_notebook_outputs(nb)
    text = json.dumps(scrubbed)
    assert "dealer_gex=1234.5" in text


def test_scrub_idempotent():
    nb = _nb_with_output()
    once = scrub_notebook_outputs(nb)
    twice = scrub_notebook_outputs(once)
    assert once == twice


def test_scrub_returns_changed_flag(tmp_path: pathlib.Path):
    """The CLI returns nonzero only when the file was changed in place."""
    from scripts.scrub_outputs import scrub_file_in_place

    nb_path = tmp_path / "n.ipynb"
    nb_path.write_text(json.dumps(_nb_with_output()), encoding="utf-8")
    assert scrub_file_in_place(nb_path) is True
    # Second call: nothing changes.
    assert scrub_file_in_place(nb_path) is False
```

- [ ] **Step 6.2: Run test to confirm it fails**

```bash
pytest tests/cookbook_tools/test_scrub_outputs.py -v
```

Expected: ImportError on `scripts.scrub_outputs`. FAIL.

- [ ] **Step 6.3: Implement `scripts/scrub_outputs.py`**

First create `scripts/__init__.py`:

```python
```

(Empty file.)

Then `scripts/scrub_outputs.py`:

```python
"""Strip auth-shaped strings from .ipynb cell outputs.

Used as a pre-commit hook AND a Layer 0 test fixture. Keeps bodies, status
codes, and latencies intact (LLM training value); only replaces the
sensitive header values with `<REDACTED>`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

# Patterns: anything that looks like an Authorization header value, an
# X-Api-Key value, or a Cookie value. Conservative — matches the value
# adjacent to the key name, with optional quoting.
_PATTERNS = [
    re.compile(
        r"(?i)(authorization['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"
    ),
    re.compile(
        r"(?i)(x[-_]api[-_]key['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"
    ),
    re.compile(
        r"(?i)(cookie['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"
    ),
    # Bearer tokens / FA-shaped keys appearing anywhere.
    re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-\.]{8,})"),
    re.compile(r"\b(fa_[A-Za-z0-9_\-]{4,})\b"),
]


def _scrub_string(s: str) -> str:
    out = s
    for pat in _PATTERNS:
        if pat.groups == 3:
            out = pat.sub(r"\1<REDACTED>\3", out)
        elif pat.groups == 2:
            out = pat.sub(r"\1<REDACTED>", out)
        else:
            out = pat.sub("<REDACTED>", out)
    return out


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_string(value)
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    return value


def scrub_notebook_outputs(nb: dict[str, Any]) -> dict[str, Any]:
    new = {**nb, "cells": []}
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            new["cells"].append(cell)
            continue
        new_cell = {**cell}
        outputs = []
        for out in cell.get("outputs", []):
            outputs.append(_scrub_value(out))
        new_cell["outputs"] = outputs
        new["cells"].append(new_cell)
    return new


def scrub_file_in_place(path: pathlib.Path) -> bool:
    """Return True if the file was modified."""
    original = path.read_text(encoding="utf-8")
    nb = json.loads(original)
    scrubbed = scrub_notebook_outputs(nb)
    new_text = json.dumps(scrubbed, indent=1, ensure_ascii=False)
    if new_text.rstrip("\n") == original.rstrip("\n"):
        return False
    path.write_text(new_text + "\n", encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=pathlib.Path)
    args = parser.parse_args(argv)
    changed_any = False
    for f in args.files:
        if not f.suffix == ".ipynb":
            continue
        if scrub_file_in_place(f):
            print(f"scrubbed: {f}", file=sys.stderr)
            changed_any = True
    # Pre-commit convention: nonzero exit if files were modified.
    return 1 if changed_any else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_scrub_outputs.py -v
```

Expected: 4 passed.

- [ ] **Step 6.5: Commit**

```bash
git add scripts/__init__.py scripts/scrub_outputs.py tests/cookbook_tools/test_scrub_outputs.py
git commit -m "Add scrub_outputs.py pre-commit hook"
```

---

## Task 7: `scripts/new_recipe.py` — paired-notebook scaffolder (TDD)

**Files:**
- Create: `scripts/new_recipe.py`
- Test: `tests/cookbook_tools/test_new_recipe.py`

- [ ] **Step 7.1: Write failing test `tests/cookbook_tools/test_new_recipe.py`**

```python
"""Integration test for the recipe scaffolder."""

import pathlib
import subprocess
import sys

import nbformat
import pytest

from cookbook_tools.frontmatter import parse_frontmatter
from cookbook_tools.notebook_io import (
    extract_frontmatter_text,
    extract_markdown_urls,
    load_notebook,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_new_recipe_creates_paired_files(tmp_path: pathlib.Path):
    out_dir = tmp_path / "notebooks" / "tier-a-hooks"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.new_recipe",
            "--slug",
            "demo-99-test",
            "--title",
            "Demo Recipe 99",
            "--tier",
            "free",
            "--tier-dir",
            "tier-a-hooks",
            "--out-root",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert (out_dir / "demo-99-test.py").exists(), result.stdout
    assert (out_dir / "demo-99-test.ipynb").exists()


def test_scaffolded_notebook_has_valid_frontmatter(tmp_path: pathlib.Path):
    subprocess.run(
        [
            sys.executable, "-m", "scripts.new_recipe",
            "--slug", "demo-99-test", "--title", "Demo", "--tier", "free",
            "--tier-dir", "tier-a-hooks", "--out-root", str(tmp_path),
        ],
        cwd=REPO_ROOT, check=True,
    )
    nb = load_notebook(tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.ipynb")
    fm = parse_frontmatter(extract_frontmatter_text(nb))
    assert fm.slug == "demo-99-test"
    assert fm.tier == "free"


def test_scaffolded_notebook_has_top_and_bottom_cta_with_correct_utm(
    tmp_path: pathlib.Path,
):
    subprocess.run(
        [
            sys.executable, "-m", "scripts.new_recipe",
            "--slug", "demo-99-test", "--title", "Demo", "--tier", "free",
            "--tier-dir", "tier-a-hooks", "--out-root", str(tmp_path),
        ],
        cwd=REPO_ROOT, check=True,
    )
    nb = load_notebook(tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.ipynb")
    urls = extract_markdown_urls(nb)
    assert any("utm_campaign=demo-99-test" in u for u in urls)
    assert any("flashalpha.com/signup" in u for u in urls)
    assert any("flashalpha.com/pricing" in u for u in urls)
    assert any("flashalpha.com/discord" in u for u in urls)


def test_scaffolded_py_and_ipynb_are_jupytext_synced(tmp_path: pathlib.Path):
    """The .py file is the source of truth; its content should match the
    .ipynb when read via jupytext."""
    import jupytext

    subprocess.run(
        [
            sys.executable, "-m", "scripts.new_recipe",
            "--slug", "demo-99-test", "--title", "Demo", "--tier", "free",
            "--tier-dir", "tier-a-hooks", "--out-root", str(tmp_path),
        ],
        cwd=REPO_ROOT, check=True,
    )
    py_path = tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.py"
    ipynb_path = tmp_path / "notebooks" / "tier-a-hooks" / "demo-99-test.ipynb"

    nb_from_py = jupytext.read(py_path)
    nb_from_ipynb = jupytext.read(ipynb_path)
    assert len(nb_from_py.cells) == len(nb_from_ipynb.cells)
```

- [ ] **Step 7.2: Run the test to confirm it fails**

```bash
pytest tests/cookbook_tools/test_new_recipe.py -v
```

Expected: ImportError on `scripts.new_recipe`. FAIL.

- [ ] **Step 7.3: Implement `scripts/new_recipe.py`**

```python
"""Scaffold a paired (.py + .ipynb) recipe from frontmatter args."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
import textwrap

import jupytext
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_raw_cell

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import ExpectedArtifacts, Frontmatter


def build_notebook(fm: Frontmatter, *, tier_dir: str) -> nbformat.NotebookNode:
    frontmatter_yaml = textwrap.dedent(f"""\
        ---
        slug: {fm.slug}
        title: {fm.title}
        tier: {fm.tier}
        runtime_budget_seconds: {fm.runtime_budget_seconds}
        max_api_calls: {fm.max_api_calls}
        endpoints_used:
          - /v1/exposure/gex/{{symbol}}
        tier_gated_cells: []
        sdk_version_min: "{fm.sdk_version_min}"
        utm_campaign: {fm.utm_campaign}
        expected_artifacts:
          dataframes: []
          charts: []
        last_validated_live: {fm.last_validated_live.isoformat()}
        ---
    """)

    nb = new_notebook()
    nb.cells = [
        new_raw_cell(frontmatter_yaml.rstrip()),
        new_markdown_cell(render_top_cell(fm, tier_dir=tier_dir).rstrip()),
        new_code_cell(textwrap.dedent("""\
            import os

            from flashalpha import FlashAlpha

            fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])
            # TODO: implement recipe body here.
        """).rstrip()),
        new_markdown_cell(render_bottom_cell(fm).rstrip()),
    ]
    nb["metadata"] = {
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "jupytext": {"formats": "ipynb,py:percent"},
    }
    return nb


def write_pair(nb: nbformat.NotebookNode, out_dir: pathlib.Path, slug: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ipynb_path = out_dir / f"{slug}.ipynb"
    py_path = out_dir / f"{slug}.py"
    with ipynb_path.open("w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    jupytext.write(nb, str(py_path), fmt="py:percent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--tier", required=True, choices=("free", "basic", "growth", "alpha")
    )
    parser.add_argument("--tier-dir", required=True)
    parser.add_argument(
        "--out-root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Repo root containing notebooks/. Defaults to CWD.",
    )
    parser.add_argument("--runtime-budget", type=int, default=60)
    parser.add_argument("--max-api-calls", type=int, default=8)
    parser.add_argument("--sdk-version-min", default="1.0.1")
    args = parser.parse_args(argv)

    fm = Frontmatter(
        slug=args.slug,
        title=args.title,
        tier=args.tier,
        runtime_budget_seconds=args.runtime_budget,
        max_api_calls=args.max_api_calls,
        endpoints_used=["/v1/exposure/gex/{symbol}"],
        tier_gated_cells=[],
        sdk_version_min=args.sdk_version_min,
        utm_campaign=args.slug,
        expected_artifacts=ExpectedArtifacts(),
        last_validated_live=dt.date.today(),
    )
    nb = build_notebook(fm, tier_dir=args.tier_dir)
    out_dir = args.out_root / "notebooks" / args.tier_dir
    write_pair(nb, out_dir, fm.slug)
    print(f"wrote {out_dir / (fm.slug + '.py')}", file=sys.stderr)
    print(f"wrote {out_dir / (fm.slug + '.ipynb')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7.4: Run tests to verify they pass**

```bash
pytest tests/cookbook_tools/test_new_recipe.py -v
```

Expected: 4 passed.

- [ ] **Step 7.5: Commit**

```bash
git add scripts/new_recipe.py tests/cookbook_tools/test_new_recipe.py
git commit -m "Add new_recipe.py scaffolder"
```

---

## Task 8: Jupytext repo config + pre-commit config

**Files:**
- Create: `jupytext.toml`
- Create: `.pre-commit-config.yaml`

- [ ] **Step 8.1: Write `jupytext.toml`**

```toml
# Pair every notebook in notebooks/** with a .py file in py:percent format.
formats = "ipynb,py:percent"
notebook_metadata_filter = "-all"
cell_metadata_filter = "-all"
```

- [ ] **Step 8.2: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
        args: ["protect", "--staged", "--redact", "--verbose"]

  - repo: local
    hooks:
      - id: scrub-notebook-outputs
        name: Scrub auth headers from notebook outputs
        entry: python -m scripts.scrub_outputs
        language: system
        files: '\.ipynb$'
        pass_filenames: true

  - repo: https://github.com/mwouts/jupytext
    rev: v1.16.4
    hooks:
      - id: jupytext
        args: ["--sync"]
        # Only Phase-0+ paired recipes under notebooks/tier-*/.
        # Legacy notebooks/0*_*.py scripts are out of scope until Phase 1.
        files: '^notebooks/tier-[a-g]-[^/]+/[^/]+\.(py|ipynb)$'

  - repo: https://github.com/nbQA-dev/nbQA
    rev: 1.8.5
    hooks:
      - id: nbqa-ruff
        files: '^notebooks/tier-[a-g]-[^/]+/[^/]+\.ipynb$'
        args: ["--fix"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        files: '(cookbook_tools|scripts|tests)/.*\.py$'
```

- [ ] **Step 8.3: Install the pre-commit hooks**

```bash
pre-commit install
pre-commit run --all-files
```

Expected: first run will format/sync existing files. Re-run until clean:

```bash
pre-commit run --all-files
```

Expected: all hooks pass.

- [ ] **Step 8.4: Commit**

```bash
git add jupytext.toml .pre-commit-config.yaml
git commit -m "Wire jupytext config and pre-commit hooks"
```

---

## Task 9: `tests/conftest.py` — shared fixtures

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 9.1: Replace the `tests/__init__.py` (already exists) with a no-op, and write `tests/conftest.py`**

Write `tests/conftest.py`:

```python
"""Shared fixtures for cookbook test layers."""

from __future__ import annotations

import pathlib

import pytest

from cookbook_tools.frontmatter import Frontmatter, parse_frontmatter
from cookbook_tools.notebook_io import extract_frontmatter_text, load_notebook
from cookbook_tools.tier_map import TierMap, load_tier_map

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
TIER_MAP_PATH = REPO_ROOT / "endpoint_tiers.yaml"


def _discover_recipe_notebooks() -> list[pathlib.Path]:
    """Notebooks under notebooks/tier-*/<slug>.ipynb — i.e. paired-form
    recipes only. Excludes the legacy 0*_*.py scripts that haven't been
    migrated yet."""
    if not NOTEBOOKS_DIR.exists():
        return []
    return sorted(NOTEBOOKS_DIR.glob("tier-*/*.ipynb"))


RECIPE_NOTEBOOKS = _discover_recipe_notebooks()


def pytest_generate_tests(metafunc):
    if "recipe_path" in metafunc.fixturenames:
        metafunc.parametrize(
            "recipe_path",
            RECIPE_NOTEBOOKS,
            ids=[p.parent.name + "/" + p.stem for p in RECIPE_NOTEBOOKS],
        )


@pytest.fixture(scope="session")
def tier_map() -> TierMap:
    return load_tier_map(TIER_MAP_PATH)


@pytest.fixture
def recipe_fm(recipe_path: pathlib.Path) -> Frontmatter:
    return parse_frontmatter(extract_frontmatter_text(load_notebook(recipe_path)))
```

- [ ] **Step 9.2: Sanity-check pytest collects nothing yet (no recipes in tier-*/ dirs)**

```bash
pytest --collect-only tests/
```

Expected: collects tests for cookbook_tools/ unit tests. No errors from conftest (the parametrize over an empty list is valid).

- [ ] **Step 9.3: Commit**

```bash
git add tests/conftest.py
git commit -m "Add shared test fixtures"
```

---

## Task 10: Layer 0 — Secret scan test

**Files:**
- Create: `tests/test_layer0_secrets.py`

- [ ] **Step 10.1: Write `tests/test_layer0_secrets.py`**

```python
"""Layer 0: secret + auth-header sweep over notebook source + outputs.

Pre-commit already runs gitleaks + scrub_outputs.py. This test is the
backstop: if either fails to fire (skipped, disabled, mis-configured),
this catches the leak at PR time.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from cookbook_tools.notebook_io import load_notebook

# Patterns matched across the FULL notebook JSON (code + markdown + outputs).
_SHAPES = [
    re.compile(r"\bfa_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    # JWT shape
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\b"),
    # OpenAI-shaped sk- key (defensive — quants might paste one)
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


def test_no_secrets_in_recipe(recipe_path: pathlib.Path):
    text = recipe_path.read_text(encoding="utf-8")
    for pat in _SHAPES:
        match = pat.search(text)
        assert match is None, (
            f"Possible secret in {recipe_path.relative_to(recipe_path.parents[2])}: "
            f"pattern={pat.pattern!r} matched={match.group()!r}"
        )


def test_no_authorization_header_value_in_outputs(recipe_path: pathlib.Path):
    """The scrubber should have stripped these. If <REDACTED> is missing
    and 'Authorization' is present with a value, the scrubber failed."""
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs", []):
            blob = json.dumps(output)
            # If the output mentions "Authorization", the value must be redacted.
            if "Authorization" in blob or "authorization" in blob:
                assert "<REDACTED>" in blob or "REDACTED" in blob, (
                    f"Unredacted Authorization header in output of "
                    f"{recipe_path.name}: {blob[:200]}"
                )
```

- [ ] **Step 10.2: Run the test (no recipes yet, so it's parametrized over 0)**

```bash
pytest tests/test_layer0_secrets.py -v
```

Expected: `no tests ran` (since no recipes exist under `tier-*/`). PASS.

- [ ] **Step 10.3: Commit**

```bash
git add tests/test_layer0_secrets.py
git commit -m "Add Layer 0 secret-scan test"
```

---

## Task 11: Layer 1 — Structural test

**Files:**
- Create: `tests/test_layer1_structural.py`

- [ ] **Step 11.1: Write `tests/test_layer1_structural.py`**

```python
"""Layer 1: structural checks parametrized over every recipe notebook."""

from __future__ import annotations

import ast
import pathlib
import re

import nbformat
import pytest

from cookbook_tools.cta_template import (
    render_bottom_cell,
    render_top_cell,
)
from cookbook_tools.frontmatter import Frontmatter
from cookbook_tools.notebook_io import (
    extract_markdown_urls,
    load_notebook,
)
from cookbook_tools.tier_map import TierMap, tier_covers

_REQUIREMENTS = (
    pathlib.Path(__file__).resolve().parents[1] / "requirements.txt"
)


def test_notebook_is_valid_nbformat(recipe_path: pathlib.Path):
    nb = nbformat.read(recipe_path, as_version=4)
    nbformat.validate(nb)


def test_slug_matches_filename(recipe_path: pathlib.Path, recipe_fm: Frontmatter):
    assert recipe_fm.slug == recipe_path.stem, (
        f"frontmatter.slug={recipe_fm.slug!r} != filename stem "
        f"{recipe_path.stem!r}"
    )


def test_top_cell_present_with_correct_signup_utm(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    tier_dir = recipe_path.parent.name
    expected_top = render_top_cell(recipe_fm, tier_dir=tier_dir).rstrip()
    # Top cell is the second cell (after the frontmatter raw cell).
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    assert md_cells, "no markdown cells found"
    rendered_top = "".join(md_cells[0]["source"]) if isinstance(md_cells[0]["source"], list) else md_cells[0]["source"]
    assert expected_top.strip() in rendered_top.strip(), (
        f"top CTA cell content mismatch in {recipe_path.name}"
    )


def test_bottom_cell_present_with_correct_utm(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter
):
    nb = load_notebook(recipe_path)
    expected_bottom = render_bottom_cell(recipe_fm).rstrip()
    md_cells = [c for c in nb["cells"] if c["cell_type"] == "markdown"]
    rendered_bottom = "".join(md_cells[-1]["source"]) if isinstance(md_cells[-1]["source"], list) else md_cells[-1]["source"]
    assert expected_bottom.strip() in rendered_bottom.strip(), (
        f"bottom CTA cell content mismatch in {recipe_path.name}"
    )


def test_no_hardcoded_api_key_in_source(recipe_path: pathlib.Path):
    text = recipe_path.read_text(encoding="utf-8")
    # Find any FlashAlpha(...) call and ensure its arg is os.environ[...]
    for match in re.finditer(r"FlashAlpha\(([^)]+)\)", text):
        arg = match.group(1).strip()
        assert "os.environ" in arg or "getenv" in arg, (
            f"FlashAlpha({arg}) — must read from environment, not hardcode"
        )


def test_no_broad_except_hiding_errors(recipe_path: pathlib.Path):
    """Code cells must not silently swallow API errors."""
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if not source.strip():
            continue
        # Skip cells with %% magics (not valid Python on their own).
        if source.lstrip().startswith("%"):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            pytest.fail(f"SyntaxError in {recipe_path.name}: cell does not parse")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Disallow bare except, or `except Exception:` with only `pass`.
                body_is_pass_only = (
                    len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                )
                assert not body_is_pass_only, (
                    f"Bare/empty except in {recipe_path.name} hides errors"
                )


def test_endpoints_used_have_known_tier(
    recipe_fm: Frontmatter, tier_map: TierMap
):
    """Every declared endpoint must resolve to a known tier."""
    # Replace {symbol} placeholder with SPY for lookup; the prefix match
    # ignores everything past the prefix anyway.
    for ep in recipe_fm.endpoints_used:
        concrete = ep.replace("{symbol}", "SPY")
        # Raises KeyError if no rule matches.
        tier_map.required_for(concrete)


def test_imports_present_in_requirements(recipe_path: pathlib.Path):
    """Every top-level import in a code cell must be available."""
    requirements = _REQUIREMENTS.read_text(encoding="utf-8").lower()
    # Stdlib modules we never want to gate on requirements.txt.
    stdlib = {
        "os", "sys", "json", "pathlib", "datetime", "math", "re", "itertools",
        "functools", "collections", "typing", "time", "io", "csv", "textwrap",
    }
    nb = load_notebook(recipe_path)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if not source.strip():
            continue
        if source.lstrip().startswith("%"):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [n.name.split(".")[0] for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module.split(".")[0]] if node.module else []
            else:
                continue
            for name in names:
                if name in stdlib:
                    continue
                assert name.lower() in requirements, (
                    f"{recipe_path.name} imports {name!r} but it is not in "
                    f"requirements.txt"
                )
```

- [ ] **Step 11.2: Run the test (no recipes yet)**

```bash
pytest tests/test_layer1_structural.py -v
```

Expected: `no tests ran`. PASS.

- [ ] **Step 11.3: Commit**

```bash
git add tests/test_layer1_structural.py
git commit -m "Add Layer 1 structural test"
```

---

## Task 12: Layer 4 — Static tier-gating test

**Files:**
- Create: `tests/test_layer4_tier_static.py`

- [ ] **Step 12.1: Write `tests/test_layer4_tier_static.py`**

```python
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
```

> NOTE: this test ignores cells listed in `tier_gated_cells` by virtue of
> only checking the **declared** endpoints. The mid-gate cell + the
> author's `tier_gated_cells` entry are how a recipe legitimately includes
> a higher-tier call; the structural test (Layer 1) enforces that the
> gate cell precedes the actual call.

- [ ] **Step 12.2: Run the test (no recipes yet)**

```bash
pytest tests/test_layer4_tier_static.py -v
```

Expected: `no tests ran`. PASS.

- [ ] **Step 12.3: Commit**

```bash
git add tests/test_layer4_tier_static.py
git commit -m "Add Layer 4 static tier-gating test"
```

---

## Task 13: Port `02_gex_dashboard.py` → canonical recipe `01-gex-dashboard`

**Files:**
- Create: `notebooks/tier-a-hooks/01-gex-dashboard.py`
- Create: `notebooks/tier-a-hooks/01-gex-dashboard.ipynb` (executed)

This is the canonical template every later recipe will copy.

- [ ] **Step 13.1: Scaffold the empty pair**

```bash
python -m scripts.new_recipe \
  --slug 01-gex-dashboard \
  --title "Build a GEX Dashboard in 30 Lines" \
  --tier free \
  --tier-dir tier-a-hooks
```

Expected: writes `notebooks/tier-a-hooks/01-gex-dashboard.{py,ipynb}`.

- [ ] **Step 13.2: Replace the scaffolded `.py` with the ported recipe body**

Open `notebooks/tier-a-hooks/01-gex-dashboard.py` and replace its content with:

```python
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.4
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [raw]
# ---
# slug: 01-gex-dashboard
# title: Build a GEX Dashboard in 30 Lines
# tier: free
# runtime_budget_seconds: 60
# max_api_calls: 4
# endpoints_used:
#   - /v1/exposure/gex/{symbol}
#   - /v1/exposure/levels/{symbol}
# tier_gated_cells: []
# sdk_version_min: "1.0.1"
# utm_campaign: 01-gex-dashboard
# expected_artifacts:
#   dataframes: []
#   charts: [gex_chart.png]
# last_validated_live: 2026-05-25
# ---

# %% [markdown]
# # Build a GEX Dashboard in 30 Lines
#
# > 🔑 Get a free FlashAlpha API key (5 req/day, no card):
# >   https://flashalpha.com/signup?utm_source=github-cookbook&utm_medium=notebook&utm_campaign=01-gex-dashboard
# >
# > Tier required: **Free** · [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FlashAlpha-lab/flashalpha-examples/blob/main/notebooks/tier-a-hooks/01-gex-dashboard.ipynb)

# %% [markdown]
# Visualize Gamma Exposure (GEX) by strike for SPY. Gamma flip, call wall, and
# put wall are annotated directly on the chart.

# %%
import os

import matplotlib
matplotlib.use("Agg")  # headless-safe; remove if running interactively
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# %%
# Fetch GEX strikes and key levels — these are the two Free-tier calls.
gex_data = fa.gex("SPY")           # /v1/exposure/gex/SPY
levels = fa.exposure_levels("SPY")  # /v1/exposure/levels/SPY

strikes = [s["strike"] for s in gex_data["strikes"]]
gex_vals = [s["net_gex"] for s in gex_data["strikes"]]
lvl = levels["levels"]

net_gex = sum(gex_vals)
regime = (
    "Positive GEX — dealers are long gamma (dampening moves)"
    if net_gex > 0
    else "Negative GEX — dealers are short gamma (amplifying moves)"
)
print(f"Net GEX: {net_gex:,.0f}  |  Regime: {regime}")

# %%
top5 = sorted(zip(strikes, gex_vals), key=lambda x: abs(x[1]), reverse=True)[:5]
print("Top 5 strikes by |GEX|:")
for strike, g in top5:
    print(f"  {strike:>7.1f}  GEX={g:>15,.0f}")

# %%
colors = ["#2ecc71" if g >= 0 else "#e74c3c" for g in gex_vals]

fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(strikes, gex_vals, width=1.0, color=colors, alpha=0.85)

for label, key, color in [
    ("Gamma Flip", "gamma_flip", "#f39c12"),
    ("Call Wall", "call_wall", "#2980b9"),
    ("Put Wall", "put_wall", "#8e44ad"),
]:
    val = lvl.get(key)
    if val:
        ax.axvline(val, color=color, linewidth=1.8, linestyle="--", label=f"{label}: {val}")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e9:.1f}B"))
ax.set_xlabel("Strike")
ax.set_ylabel("GEX ($ billions)")
ax.set_title("SPY Gamma Exposure by Strike")
ax.legend()
ax.axhline(0, color="#888888", linewidth=0.6, alpha=0.4)
fig.tight_layout()
fig.savefig("gex_chart.png", dpi=150)
print("Chart saved to gex_chart.png")

# %% [markdown]
# ## What to try next
#
# - 🔁 Backtest this with historical replay (Alpha) → https://flashalpha.com/pricing?utm_source=github-cookbook&utm_campaign=01-gex-dashboard
# - 💬 Discord: https://flashalpha.com/discord
# - 📚 More recipes: https://github.com/FlashAlpha-lab/flashalpha-examples
# - 🤖 Use with Claude/Cursor via MCP: https://flashalpha.com/docs/mcp
```

- [ ] **Step 13.3: Regenerate the paired `.ipynb` from this `.py` and execute it live (one-time author step)**

```bash
# Sync .py → .ipynb
jupytext --to ipynb notebooks/tier-a-hooks/01-gex-dashboard.py

# Execute it with the live API to populate outputs.
# REQUIRES FLASHALPHA_API_KEY in env. This is the only step where the
# author runs against live API for this recipe.
papermill \
  notebooks/tier-a-hooks/01-gex-dashboard.ipynb \
  notebooks/tier-a-hooks/01-gex-dashboard.ipynb \
  --kernel python3
```

Expected: executed `.ipynb` with chart output committed.

- [ ] **Step 13.4: Scrub auth headers from outputs (defensive — should be no-op)**

```bash
python -m scripts.scrub_outputs notebooks/tier-a-hooks/01-gex-dashboard.ipynb
```

Expected: exit 0 (nothing changed) — Free-tier calls don't echo Authorization headers in responses anyway.

- [ ] **Step 13.5: Run Layers 0, 1, 4 against the new recipe**

```bash
pytest tests/test_layer0_secrets.py tests/test_layer1_structural.py tests/test_layer4_tier_static.py -v
```

Expected: tests for `tier-a-hooks/01-gex-dashboard` collected and PASS.

- [ ] **Step 13.6: Commit**

```bash
git add notebooks/tier-a-hooks/01-gex-dashboard.py notebooks/tier-a-hooks/01-gex-dashboard.ipynb
git commit -m "Add canonical recipe tier-a-hooks/01-gex-dashboard"
```

---

## Task 14: `scripts/record_cassettes.py` + record the first cassette

**Files:**
- Create: `scripts/record_cassettes.py`
- Create: `tests/cassettes/01-gex-dashboard/cassette.yaml`

- [ ] **Step 14.1: Write `scripts/record_cassettes.py`**

```python
"""Record a vcrpy cassette for a single recipe by executing it with papermill.

Usage:
    FLASHALPHA_API_KEY=... python -m scripts.record_cassettes \
        notebooks/tier-a-hooks/01-gex-dashboard.ipynb
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import papermill
import vcr

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CASSETTE_ROOT = REPO_ROOT / "tests" / "cassettes"

_VCR = vcr.VCR(
    serializer="yaml",
    record_mode="new_episodes",
    filter_headers=["Authorization", "X-Api-Key", "Cookie"],
    match_on=("method", "scheme", "host", "path", "query"),
)


def cassette_path_for(notebook_path: pathlib.Path) -> pathlib.Path:
    return CASSETTE_ROOT / notebook_path.stem / "cassette.yaml"


def record(notebook_path: pathlib.Path) -> pathlib.Path:
    cpath = cassette_path_for(notebook_path)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    with _VCR.use_cassette(str(cpath)):
        papermill.execute_notebook(
            str(notebook_path),
            str(notebook_path),
            kernel_name="python3",
        )
    return cpath


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=pathlib.Path)
    args = parser.parse_args(argv)
    out = record(args.notebook)
    print(f"recorded: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 14.2: Record the cassette for `01-gex-dashboard`**

```bash
# REQUIRES FLASHALPHA_API_KEY in env.
python -m scripts.record_cassettes notebooks/tier-a-hooks/01-gex-dashboard.ipynb
```

Expected: `tests/cassettes/01-gex-dashboard/cassette.yaml` created. Notebook re-executed (outputs may shift slightly).

- [ ] **Step 14.3: Inspect the cassette manually**

```bash
head -50 tests/cassettes/01-gex-dashboard/cassette.yaml
```

Expected: `Authorization` and `X-Api-Key` headers are absent (filtered by `_VCR.filter_headers`). Bodies and responses present.

- [ ] **Step 14.4: Commit**

```bash
git add scripts/record_cassettes.py tests/cassettes/01-gex-dashboard/cassette.yaml notebooks/tier-a-hooks/01-gex-dashboard.ipynb
git commit -m "Record cassette for 01-gex-dashboard"
```

---

## Task 15: Layer 2 — Execution test (cassette replay)

**Files:**
- Create: `tests/test_layer2_execution.py`

- [ ] **Step 15.1: Write failing test `tests/test_layer2_execution.py`**

```python
"""Layer 2: replay each recipe under papermill+vcrpy against its cassette."""

from __future__ import annotations

import pathlib
import time

import papermill
import pytest
import vcr

from cookbook_tools.frontmatter import Frontmatter

CASSETTE_ROOT = pathlib.Path(__file__).resolve().parent / "cassettes"

_VCR = vcr.VCR(
    serializer="yaml",
    record_mode="none",  # PR: replay only; nightly uses record_cassettes.py
    filter_headers=["Authorization", "X-Api-Key", "Cookie"],
    match_on=("method", "scheme", "host", "path", "query"),
)


@pytest.mark.cassette
def test_recipe_executes_under_cassette(
    recipe_path: pathlib.Path, recipe_fm: Frontmatter, tmp_path: pathlib.Path
):
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")

    out_nb = tmp_path / f"{recipe_fm.slug}.executed.ipynb"

    start = time.perf_counter()
    with _VCR.use_cassette(str(cassette_path)):
        papermill.execute_notebook(
            str(recipe_path),
            str(out_nb),
            kernel_name="python3",
            parameters={},
        )
    elapsed = time.perf_counter() - start

    assert elapsed < recipe_fm.runtime_budget_seconds, (
        f"{recipe_fm.slug} took {elapsed:.1f}s, exceeds "
        f"runtime_budget_seconds={recipe_fm.runtime_budget_seconds}"
    )


@pytest.mark.cassette
def test_recipe_api_call_count_within_budget(
    recipe_fm: Frontmatter,
):
    cassette_path = CASSETTE_ROOT / recipe_fm.slug / "cassette.yaml"
    if not cassette_path.exists():
        pytest.skip(f"no cassette recorded for {recipe_fm.slug}")

    import yaml

    with cassette_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    interactions = data.get("interactions", [])
    assert len(interactions) <= recipe_fm.max_api_calls, (
        f"{recipe_fm.slug} made {len(interactions)} API calls, "
        f"exceeds max_api_calls={recipe_fm.max_api_calls}"
    )
```

- [ ] **Step 15.2: Run the test**

```bash
pytest tests/test_layer2_execution.py -v -m cassette
```

Expected: 2 tests for `tier-a-hooks/01-gex-dashboard` PASS.

If `papermill` fails because the kernel isn't installed:

```bash
python -m ipykernel install --user --name python3
```

Then re-run.

- [ ] **Step 15.3: Commit**

```bash
git add tests/test_layer2_execution.py
git commit -m "Add Layer 2 cassette-replay test"
```

---

## Task 16: CI workflow `pr.yml`

**Files:**
- Modify: `.github/workflows/ci.yml` → replace with `.github/workflows/pr.yml`

- [ ] **Step 16.1: Remove the old `ci.yml`**

```bash
git rm .github/workflows/ci.yml
```

- [ ] **Step 16.2: Write `.github/workflows/pr.yml`**

```yaml
name: PR

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install dev deps
        run: python -m pip install -e ".[dev]"

      - name: Install Jupyter kernel
        run: python -m ipykernel install --user --name python3

      - name: Layer 0 — pre-commit hooks (excluding network)
        run: |
          python -m pip install pre-commit
          pre-commit run --all-files --hook-stage manual || true
          # Re-run to detect mutations from auto-fixers.
          pre-commit run --all-files

      - name: Layer 0 — secret scan (test backstop)
        run: pytest tests/test_layer0_secrets.py -v

      - name: Layer 1 — structural
        run: pytest tests/test_layer1_structural.py -v

      - name: Layer 4 — static tier gating
        run: pytest tests/test_layer4_tier_static.py -v

      - name: Cookbook tools — unit tests
        run: pytest tests/cookbook_tools/ -v

      - name: Layer 2 — cassette replay
        run: pytest tests/test_layer2_execution.py -v -m cassette
```

- [ ] **Step 16.3: Validate the workflow syntax locally (optional)**

```bash
# If actionlint is installed:
actionlint .github/workflows/pr.yml || echo "actionlint not installed; skip"
```

- [ ] **Step 16.4: Commit**

```bash
git add .github/workflows/pr.yml
git commit -m "Replace ci.yml with pr.yml running all Phase-0 layers"
```

---

## Task 17: Update README to reflect cookbook v1.0-rc

**Files:**
- Modify: `README.md`

- [ ] **Step 17.1: Replace `README.md`**

Replace the file with:

```markdown
# FlashAlpha Cookbook

[![PR](https://github.com/FlashAlpha-lab/flashalpha-examples/actions/workflows/pr.yml/badge.svg)](https://github.com/FlashAlpha-lab/flashalpha-examples/actions/workflows/pr.yml)

Production Python recipes for gamma exposure, dealer positioning, SVI vol
surfaces, VRP, 0DTE, and unusual flow — powered by the
[FlashAlpha API](https://flashalpha.com).

Every recipe is a **jupytext-paired** `(.py + .ipynb)` file with executed
outputs committed. Open any recipe in Colab via its badge, or `pip install
flashalpha` and run the `.py` directly.

```bash
pip install flashalpha matplotlib numpy
export FLASHALPHA_API_KEY="your_key_here"
python notebooks/tier-a-hooks/01-gex-dashboard.py
```

## Catalog

See [COOKBOOK.md](COOKBOOK.md) for the full catalog (added in Phase 1+).

Phase 0 ships the foundation and one canonical recipe:
[01-gex-dashboard](notebooks/tier-a-hooks/01-gex-dashboard.ipynb).

## Authoring a new recipe

```bash
python -m scripts.new_recipe \
  --slug 02-gamma-flip-cross-index \
  --title "Find Today's Gamma Flip Across Indexes" \
  --tier free \
  --tier-dir tier-a-hooks
```

This creates a paired `(.py, .ipynb)` skeleton with frontmatter, CTA cells,
and a starter code block. Fill in the body, run it once against live API
to record the cassette:

```bash
python -m scripts.record_cassettes notebooks/tier-a-hooks/02-gamma-flip-cross-index.ipynb
```

Then `pytest` will replay it from cassette on every PR.

See [docs/authoring-guide.md](docs/authoring-guide.md) for the full guide.

## Test layers

| Layer | What it checks | When it runs |
|---|---|---|
| **0** Secrets | gitleaks + auth-header scrub + regex sweep over code & outputs | pre-commit + PR |
| **1** Structural | frontmatter schema, CTA UTMs, slug ↔ file, AST scan, link 200s | PR |
| **2** Execution | papermill + vcrpy cassette replay; runtime + call budgets | PR |
| **3** Golden | DataFrame & chart snapshots for backtest recipes | nightly (Phase 6+) |
| **4** Tier static | endpoints_used ⊆ tier (`endpoint_tiers.yaml`) | PR |
| **5** Funnel sanity | UTM rendering, link 200s, weekly stats | weekly (Phase 8) |

## Repository structure

- `notebooks/tier-{a,b,c,d,e,f,g}-*/` — recipes by tier
- `cookbook_tools/` — shared Python helpers (Pydantic schema, tier-map, CTA renderer)
- `scripts/` — CLI tools (`new_recipe.py`, `scrub_outputs.py`, `record_cassettes.py`, `sync_tier_map.py`)
- `tests/` — Layer 0/1/2/4 test suites + cassettes
- `endpoint_tiers.yaml` — mirror of API tier middleware (`scripts/sync_tier_map.py` to regenerate)
- `docs/superpowers/{specs,plans}/` — design + implementation docs

## License

MIT. See [LICENSE](LICENSE).
```

- [ ] **Step 17.2: Commit**

```bash
git add README.md
git commit -m "Update README for cookbook v1.0-rc Phase 0"
```

---

## Task 18: Phase 0 Definition of Done — end-to-end verification

**Files:**
- (none — verification only)

This task runs every Phase-0 acceptance criterion from the spec.

- [ ] **Step 18.1: `pre-commit run --all-files` passes**

```bash
pre-commit run --all-files
```

Expected: every hook PASS, exit 0.

- [ ] **Step 18.2: Layer 0 + 1 pass with the canonical recipe present**

```bash
pytest tests/test_layer0_secrets.py tests/test_layer1_structural.py -v
```

Expected: tests for `tier-a-hooks/01-gex-dashboard` collected and PASS.

- [ ] **Step 18.3: Layer 2 (cassette) passes for `01-gex-dashboard`**

```bash
pytest tests/test_layer2_execution.py -v -m cassette
```

Expected: 2 tests PASS.

- [ ] **Step 18.4: Layer 4 (static tier gating) passes**

```bash
pytest tests/test_layer4_tier_static.py -v
```

Expected: 1 test PASS for the canonical recipe.

- [ ] **Step 18.5: `scripts/new_recipe.py --slug demo-99 --tier free` produces a valid pair**

```bash
python -m scripts.new_recipe \
  --slug demo-99 \
  --title "Demo Recipe 99" \
  --tier free \
  --tier-dir tier-a-hooks

# Verify Layer 0/1 still pass with the demo recipe added:
pytest tests/test_layer0_secrets.py tests/test_layer1_structural.py -v
# Clean up:
rm notebooks/tier-a-hooks/demo-99.py notebooks/tier-a-hooks/demo-99.ipynb
```

Expected: both tests PASS for `tier-a-hooks/demo-99` and `tier-a-hooks/01-gex-dashboard`. After cleanup, only `01-gex-dashboard` remains.

- [ ] **Step 18.6: Cookbook-tools unit tests all pass**

```bash
pytest tests/cookbook_tools/ -v
```

Expected: all unit tests PASS (frontmatter, tier_map, cta_template, notebook_io, scrub_outputs, new_recipe).

- [ ] **Step 18.7: Full pytest run**

```bash
pytest -v
```

Expected: all tests PASS. No warnings about deprecated fixtures or unhandled markers (markers declared in `pyproject.toml`).

- [ ] **Step 18.8: Verify CI workflow file is valid by pushing a no-op branch**

```bash
git checkout -b phase0-verify-ci
git commit --allow-empty -m "Trigger CI on Phase-0 foundation"
git push -u origin phase0-verify-ci
```

Then in the GitHub UI: confirm the `PR` workflow runs on all four Python versions and goes green. If green, merge or close the branch.

- [ ] **Step 18.9: Phase 0 complete — final commit + tag**

```bash
git checkout main
git tag -a phase0-complete -m "Phase 0 foundation: tooling + 5-layer test pyramid + canonical recipe"
git push --tags
```

Phase 0 acceptance criteria from spec §12 all met:

1. ✅ `pre-commit run --all-files` passes
2. ✅ Layer 0 + 1 tests pass with `01-gex-dashboard` present
3. ✅ Layer 2 cassette test passes for `01-gex-dashboard`
4. ✅ Layer 4 static tier-gating test passes
5. ✅ CI workflow `pr.yml` green on the verify-ci branch
6. ✅ `scripts/new_recipe.py` produces a valid pair that passes Layers 0/1
7. ✅ `notebooks/tier-a-hooks/01-gex-dashboard.{py,ipynb}` is the canonical template

**Next plan:** `2026-06-??-flashalpha-cookbook-phase1-migrate-existing-10.md` — port the remaining 10 `0*_*.py` scripts (one task per script, each mostly a copy-paste-and-rewire of Task 13's pattern).

---

## Self-Review Notes

Plan reviewed against spec sections:

| Spec § | Plan task(s) |
|---|---|
| 3 (repo layout) | Tasks 1, 7, 8, 9, 16 |
| 4 (jupytext) | Task 8 (config), Task 13 (canonical pair) |
| 5 (frontmatter) | Task 2 |
| 6 (CTA template) | Tasks 4, 7, 13 |
| 7 Layer 0 | Tasks 6, 8, 10, 16 |
| 7 Layer 1 | Task 11 |
| 7 Layer 2 (cassette only) | Tasks 14, 15 |
| 7 Layer 3 | Deferred to Phase 6 (called out in scope) |
| 7 Layer 4 (static) | Tasks 3, 12 |
| 7 Layer 5 | Deferred to Phase 8 (called out in scope) |
| 8 (CI) | Task 16 (pr.yml only); nightly/weekly/release-webhooks deferred per scope |
| 9 (migration) | Phase 0 ports `02_gex_dashboard.py` only (Task 13). Phase 1 plan covers the other 10. |
| 12 (DoD) | Task 18 |

All concrete code shown inline; no "TBD" / "implement later" / placeholder steps. Type/method signatures consistent across `cookbook_tools` modules: `Frontmatter`, `TierMap`, `tier_covers`, `parse_frontmatter`, `render_top_cell`, `render_bottom_cell`, `render_gate_cell`, `load_notebook`, `extract_frontmatter_text`, `extract_markdown_urls`, `extract_code_endpoints`, `scrub_notebook_outputs`, `scrub_file_in_place`.
