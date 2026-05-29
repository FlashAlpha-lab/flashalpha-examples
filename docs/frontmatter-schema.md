# Frontmatter schema

> **Auto-generated from `cookbook_tools/frontmatter.py`. Do not edit by
> hand — re-run `python -m scripts.render_schema_docs` after changing
> the Pydantic models.**

Every cookbook recipe (`notebooks/tier-*/<slug>.ipynb`) starts with a raw
cell containing YAML between `---` delimiters. The block is parsed and
validated by `cookbook_tools.frontmatter.Frontmatter` on every PR — Layer
1 fails the build on any schema violation.

## Quick example

```yaml
---
slug: 01-gex-dashboard
title: Build a GEX Dashboard in 30 Lines
tier: free
runtime_budget_seconds: 60
max_api_calls: 4
endpoints_used:
  - /v1/exposure/gex/{symbol}
  - /v1/exposure/levels/{symbol}
tier_gated_cells: []
sdk_version_min: "1.0.1"
utm_campaign: 01-gex-dashboard
expected_artifacts:
  dataframes: []
  charts: [gex_chart.png]
last_validated_live: 2026-05-27
---
```

You normally do not write this by hand — `scripts/new_recipe.py`
scaffolds the entire block from CLI args.

## Field reference

### `Frontmatter`

The structurally enforced metadata block at the top of every recipe.

Authors do NOT write this by hand — `scripts/new_recipe.py` scaffolds
it from CLI args. Layer 1 (structural test) enforces that every field
is present and valid on every commit.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `slug` | `str` | yes | — | Kebab-case identifier, must match the filename stem and the UTM campaign. Used as the recipe's primary key across cassettes, snapshots, and analytics. |
| `title` | `str` | yes | — | Human-readable title shown as the H1 of the recipe's top markdown cell. Should be short enough to fit in a Colab tab (~60 chars). Markdown-special characters are allowed. |
| `tier` | `'free' \| 'basic' \| 'growth' \| 'alpha'` | yes | — | Minimum FlashAlpha subscription tier required to run the recipe end-to-end. One of: free, basic, growth, alpha. The tier display name (Free/Basic/Growth/Alpha) appears in the top CTA cell. Layer 4 asserts every endpoint in `endpoints_used` resolves to a tier ≤ this value, OR the calling cell is listed in `tier_gated_cells`. |
| `runtime_budget_seconds` | `int (>0)` | yes | — | Maximum wall-clock seconds the recipe is allowed to run under Layer 2 cassette replay. Exceeding this fails the PR build. Tighten as the recipe matures; default 60s. |
| `max_api_calls` | `int (>0)` | yes | — | Maximum number of FlashAlpha API interactions the recipe is allowed to make. Layer 2 asserts the cassette interaction count is ≤ this value (and ≥ value-2 to prevent budget padding). |
| `endpoints_used` | `list[str]` | yes | — | FlashAlpha API path templates the recipe calls. `{symbol}` is substituted with `SPY` for tier lookups. Layer 4 asserts every entry resolves to a known tier in `endpoint_tiers.yaml`, and that the resolved tier is ≤ `tier`. |
| `tier_gated_cells` | `list[int]` | no | — | Cell indices (0-based) that intentionally call an endpoint above the recipe's declared tier. Each such cell must be preceded by a mid-gate markdown cell matching `render_gate_cell(endpoint, required_tier, fm)`. Empty for tier-conforming recipes. |
| `sdk_version_min` | `str` | yes | — | Minimum `flashalpha` SDK version the recipe depends on. Used by the on-sdk-release dispatch workflow (Phase 1+) to decide which recipes to re-validate after an SDK bump. |
| `utm_campaign` | `str` | yes | — | UTM campaign string embedded in every CTA URL in the recipe. MUST equal `slug` — Layer 1 enforces. Lets the marketing funnel attribute signups back to the specific recipe that drove them. |
| `expected_artifacts` | `ExpectedArtifacts` | no | — | Names of DataFrames and chart files the recipe produces. Layer 3 (Phase 6) reads these to look up golden snapshots. Leave empty for live-data recipes; populate for deterministic backtest recipes. |
| `last_validated_live` | `date (YYYY-MM-DD)` | yes | — | Date (YYYY-MM-DD) the recipe was last successfully executed against the live API. Updated by the nightly drift job. Recipes whose date is >30 days stale appear in the weekly freshness report. |

### `ExpectedArtifacts`

Artifacts the recipe is declared to produce. Layer 3 (Phase 6) uses
these names to look up golden-snapshot files under `snapshots/<slug>/`.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `dataframes` | `list[str]` | no | — | Names of pandas DataFrames the recipe stores into the cell namespace. Each name resolves to `snapshots/<slug>/<name>.csv` for Layer 3 golden-value comparison. Empty for live-data (non-deterministic) recipes. |
| `charts` | `list[str]` | no | — | Filenames the recipe writes via `fig.savefig(name)`. Each name resolves to `snapshots/<slug>/<name>` for Layer 3 perceptual-hash comparison. |

## Tier ordering

The `tier` field accepts one of the following literals, ordered from least to most permissive:

| Tier | Index | Display name |
|---|---|---|
| `free` | 0 | Free |
| `basic` | 1 | Basic |
| `growth` | 2 | Growth |
| `alpha` | 3 | Alpha |

A recipe with `tier: growth` may use any endpoint that requires `free`, `basic`, or `growth` — i.e. `tier_covers(have, need)` returns True when `have` is at least as high as `need`.

## Validation rules

- `slug` must match `^[a-z0-9]+(-[a-z0-9]+)*$` (kebab-case)
- `utm_campaign` must equal `slug` exactly
- `runtime_budget_seconds` must be > 0
- `max_api_calls` must be > 0
- `tier_gated_cells` indices must point at code cells in the notebook (Layer 1 enforces)
- Every endpoint in `endpoints_used` must resolve to a known tier in `endpoint_tiers.yaml`, and the resolved tier must be ≤ `tier` (Layer 4 enforces)
