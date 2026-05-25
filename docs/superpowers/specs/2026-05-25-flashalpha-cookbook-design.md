# FlashAlpha Cookbook — Design

**Status:** Approved 2026-05-25
**Repo:** [FlashAlpha-lab/flashalpha-examples](https://github.com/FlashAlpha-lab/flashalpha-examples) (expanded in place; no new repo)
**Author:** solo
**Goal version:** v1.0 cookbook = 30 jupytext-paired recipes + 5-layer test pyramid + dash.flashalpha.com lead-magnet

## 1. Thesis

A code-cookbook converts API-evaluating quants better than a docs site because:

1. **Direct conversion** — quants run a recipe, hit an Alpha-gated cell, upgrade.
2. **LLM-ingestion moat** — committed `.ipynb` outputs get crawled into training data; six months out, "how do I compute dealer gamma in Python?" surfaces our recipe.
3. **Star/clone-velocity flywheel** — quants share repos; awesome-lists and newsletters pick them up. Docs pages don't get that treatment.

This spec defines the structure, format, and test discipline. Conversion attribution (UTM → signup → trial → paid) ships as a separate concern joined into the existing `11_attribution.csv` pipeline.

## 2. Scope

**In:**

- Expansion of [flashalpha-examples/](../../) from 11 `.py` scripts to 30 jupytext-paired (`.py` + `.ipynb`) recipes across seven tiers.
- 5-layer test pyramid that doubles as a downstream integration test suite for the FlashAlpha API + every released SDK.
- Conversion-funnel CTAs (top, bottom, mid-gate) enforced by structural test.
- `dash.flashalpha.com` Streamlit dashboard (Tier B recipe #11 hosted live) as the lead magnet.
- A static `endpoint_tiers.yaml` mirrored from the API's `EndpointAccessMiddleware` plus a sync script.

**Out:**

- New repo. Cookbook lives inside `flashalpha-examples`.
- MCP examples / `.cursorrules`. That stays in `flashalpha-mcp`.
- Theory deep-dives. They stay in `gex-explained`, `0dte-options-analytics`, `volatility-surface-python`; cookbook cross-links to them.
- Empirical per-tier probing (Layer 4 v2). One Alpha CI key for now; revisit in v1.1.
- Hosted notebooks server (Binder/JupyterHub). Colab badges only.

## 3. Repository layout

```
flashalpha-examples/
├── README.md                           # rewritten as cookbook front-door
├── COOKBOOK.md                         # 30-recipe catalog with Colab badges
├── CLAUDE.md                           # keep
├── LICENSE                             # keep (MIT)
├── pyproject.toml                      # bump version 0.1 → 1.0; add [project.optional-dependencies].dev
├── requirements.txt                    # runtime deps
├── requirements-dev.txt                # NEW: jupytext, papermill, nbmake, vcrpy, nbqa, ruff, pydantic
├── endpoint_tiers.yaml                 # NEW: tier map mirrored from EndpointAccessMiddleware.cs
├── notebooks/
│   ├── tier-a-hooks/                   # 7 recipes
│   ├── tier-b-dealer-flow/             # 7
│   ├── tier-c-vol-surface/             # 6
│   ├── tier-d-0dte/                    # 3
│   ├── tier-e-flow/                    # 3
│   ├── tier-f-backtest/                # 4
│   └── tier-g-engineering/             # 3
│       # each recipe: <slug>.py + <slug>.ipynb (jupytext-paired, both committed)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # papermill runner, vcrpy config, shared fixtures
│   ├── test_layer0_secrets.py          # secret + auth-header sweep beyond gitleaks
│   ├── test_layer1_structural.py       # frontmatter, CTAs, links, slug ↔ file, AST scan
│   ├── test_layer2_execution.py        # papermill + vcrpy cassettes
│   ├── test_layer3_golden.py           # backtest DataFrame snapshots + image hashes
│   ├── test_layer4_tier_static.py      # endpoints_used ⊆ allowed-by-tier static check
│   └── cassettes/<slug>/               # vcrpy recordings, one dir per recipe
├── snapshots/<slug>/                   # pytest-approval golden DataFrames + chart hashes
├── scripts/
│   ├── new_recipe.py                   # scaffold paired notebook from template + frontmatter
│   ├── scrub_outputs.py                # strip Authorization/X-Api-Key/Cookie headers from .ipynb output cells
│   ├── record_cassettes.py             # live-API recorder (one-shot per recipe)
│   ├── sync_tier_map.py                # regenerate endpoint_tiers.yaml from EndpointAccessMiddleware.cs
│   └── render_dashboard.py             # build/deploy the dash.flashalpha.com Streamlit app
├── docs/
│   ├── superpowers/specs/              # this spec lives here
│   ├── authoring-guide.md              # how to add a recipe
│   └── frontmatter-schema.md           # pydantic model documented
├── dashboard/                          # NEW: Streamlit app for #11 + Dockerfile + deploy config
│   ├── app.py
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/workflows/
│   ├── pr.yml                          # Layers 0,1,2-cassette,4 (~3 min target)
│   ├── nightly.yml                     # Layer 2-live, Layer 3, drift-PR opener (~15 min)
│   ├── weekly.yml                      # Layer 5 funnel + full lychee link check
│   ├── on-sdk-release.yml              # repository_dispatch from each SDK repo on tag
│   └── on-api-release.yml              # repository_dispatch from MC deploy
├── .pre-commit-config.yaml             # gitleaks, scrub_outputs, jupytext sync, nbqa, ruff, frontmatter
└── .gitignore                          # add .cache/, .papermill/, .pytest_cache, dashboard/.streamlit/
```

Existing `tests/test_notebooks_syntax.py` and `tests/test_examples.py` are absorbed by the new layered suite in Phase 1.

## 4. Notebook format: jupytext-paired

- **`.py` in percent format** — diff target, edited by humans, source of truth for code.
- **`.ipynb`** — source of truth for executed outputs (charts, DataFrames), regenerated by author via `papermill`, committed.
- **Pre-commit `jupytext --sync`** keeps them aligned by content (not outputs).
- **CI `jupytext --sync --check`** fails if drift.

Trade-off: every recipe is two files. Accepted because PR diffs become reviewable and grep across recipes stays fast, while still shipping committed outputs for the LLM/SEO crawl.

## 5. Frontmatter schema

Every recipe's top cell is a tagged code cell containing a YAML triple-dashed block, parsed by `pydantic` in [test_layer1_structural.py](../../tests/test_layer1_structural.py).

```yaml
---
slug: 01-gex-dashboard
title: Build a GEX Dashboard in 30 Lines
tier: free                       # free | basic | growth | alpha
runtime_budget_seconds: 60
max_api_calls: 8
endpoints_used:
  - /v1/exposure/gex/{symbol}
  - /v1/exposure/levels/{symbol}
tier_gated_cells: []             # cell indices that intentionally call above `tier`; empty = none
sdk_version_min: "1.0.1"
utm_campaign: 01-gex-dashboard
expected_artifacts:              # used by Layer 3 (backtest recipes only)
  dataframes: []
  charts: [gex_chart.png]
last_validated_live: 2026-05-25
---
```

**Enforced invariants:**

- `slug == Path(file).stem`
- `utm_campaign == slug`
- `endpoints_used ⊆ endpoint_tiers.yaml` and every endpoint's required tier ≤ `tier` (or its index is in `tier_gated_cells`)
- `last_validated_live` is updated by the nightly job whenever Layer 2-live passes

## 6. CTA template (structurally enforced)

Three fixed blocks. `scripts/new_recipe.py` renders them from frontmatter; pre-commit re-renders idempotently.

**Top markdown cell** (always first, after frontmatter):

```markdown
# {title}

> 🔑 Get a free FlashAlpha API key (5 req/day, no card):
>   https://flashalpha.com/signup?utm_source=github-cookbook&utm_medium=notebook&utm_campaign={slug}
>
> Tier required: **{tier_display}** · [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FlashAlpha-lab/flashalpha-examples/blob/main/notebooks/{tier_dir}/{slug}.ipynb)
```

**Bottom markdown cell** (always last):

```markdown
## What to try next

- 🔁 Backtest this with historical replay (Alpha) → https://flashalpha.com/pricing?utm_source=github-cookbook&utm_campaign={slug}
- 💬 Discord: https://flashalpha.com/discord
- 📚 More recipes: https://github.com/FlashAlpha-lab/flashalpha-examples
- 🤖 Use with Claude/Cursor via MCP: https://flashalpha.com/docs/mcp
```

**Mid-gate cell** (markdown, immediately before each cell whose endpoint exceeds the recipe's declared tier):

```markdown
> 🔒 The next call uses `{endpoint}` which requires **{required_tier}+**.
> Free/{lower_tier} users will get a 403 here.
> Upgrade: https://flashalpha.com/pricing?utm_source=github-cookbook&utm_campaign={slug}
```

Layer 1 enforces presence + exact UTM. Authors don't hand-type these; the scaffold script writes them and pre-commit keeps them in sync with frontmatter.

## 7. Test pyramid

### Layer 0 — Pre-commit + CI gate (~5 s)

- **gitleaks** with custom rules for `fa_*`, `flashalpha_*`, JWT/PEM shapes — scans code AND output cells.
- **scrub_outputs.py** pre-commit hook strips `Authorization`, `X-Api-Key`, `Cookie` headers from `.ipynb` output cells. Keeps bodies, status codes, latencies (preserves LLM training value).
- **jupytext --sync --check** — fails on `.py`/`.ipynb` content drift.
- **nbqa ruff check** + **nbqa black --check**.
- **Output-size caps**: 1 MB per cell, 5 MB per notebook (catches accidentally-committed screenshots).

### Layer 1 — Structural (pytest, no API, <30 s)

Parameterized over every `.ipynb`. Per recipe:

- valid nbformat JSON; round-trips through `nbformat.read`/`write` unchanged
- frontmatter validates against pydantic schema
- `slug == file.stem` and `slug == utm_campaign`
- top + bottom CTA blocks present with exact UTM string match
- every cell whose endpoint exceeds `tier` is preceded by a mid-gate cell (matched against `tier_gated_cells`)
- every import resolves from `requirements.txt`
- no hardcoded API key shape anywhere (regex sweep covers code, markdown, output)
- no `%%capture` and no broad `try/except` that silently swallows API errors (AST scan)
- outbound URLs in markdown return 200 — cached for 7 days in `.cache/links.json`; full re-check in weekly.yml via [lychee](https://github.com/lycheeverse/lychee)

### Layer 2 — Execution (PR: cassettes ~2 min; nightly: live ~10 min)

**PR path:**

- [papermill](https://papermill.readthedocs.io/) executes each notebook
- [vcrpy](https://vcrpy.readthedocs.io/) intercepts the SDK's `httpx` client; cassettes at `tests/cassettes/<slug>/`
- enforce per-recipe `runtime_budget_seconds` and `max_api_calls`
- fail if any cell raises

**Nightly path:**

- same papermill run with `record_mode=new_episodes` against live API using the single Alpha CI key
- structural diff: if cassette JSON differs at field/shape level (not values), auto-open a PR via `peter-evans/create-pull-request` containing the new cassette + a comment naming the changed endpoint and fields
- this is the API-drift early-warning system

### Layer 3 — Golden snapshots (backtest recipes only)

Applies to recipes #16, #27–30. They use historical API with locked `at=YYYY-MM-DDTHH:mm:ssZ` for determinism.

- **[pytest-approval](https://github.com/approvals/ApprovalTests.Python)** snapshots for declared `dataframes` (full CSV)
- **[imagehash](https://github.com/JohannesBuchner/imagehash)** perceptual hash for declared `charts`; Hamming-distance tolerance ≥ 4 bits (catches blank / sign-flipped charts; tolerates matplotlib font-rendering changes)
- snapshots live at `snapshots/<slug>/`; diff requires human re-approval

### Layer 4 — Static tier-gating (with one Alpha key)

Because the canonical tier map lives in C# code at [EndpointAccessMiddleware.cs:60](../../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs) and we only have one Alpha CI key (no per-tier probing), the cookbook ships **`endpoint_tiers.yaml`** mirroring that map.

Per recipe:

- for each endpoint in `endpoints_used`, look up its required tier in `endpoint_tiers.yaml`
- assert `required_tier ≤ frontmatter.tier` OR the cell index appears in `tier_gated_cells`

A separate test verifies the YAML's structural integrity (all endpoints map to a known tier, no orphans).

**Sample `endpoint_tiers.yaml`** (excerpt mirroring [EndpointAccessMiddleware.cs:60](../../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs#L60)):

```yaml
# Generated 2026-05-25 by scripts/sync_tier_map.py from EndpointAccessMiddleware.cs
# DO NOT EDIT BY HAND — run the sync script.
tiers:
  - free
  - basic
  - growth
  - alpha
rules:
  # ordered most-specific first; first match wins (mirrors middleware semantics)
  - prefix: /v1/vrp/                            ; required: alpha
  - prefix: /v1/flow/levels/                    ; required: growth
  - prefix: /v1/flow/pin-risk/                  ; required: growth
  - prefix: /v1/flow/dealer-risk/               ; required: growth
  - prefix: /v1/flow/                           ; required: alpha
  - prefix: /v1/earnings/vrp/                   ; required: alpha
  - prefix: /v1/earnings/dealer-positioning/    ; required: alpha
  - prefix: /v1/earnings/                       ; required: growth
  - prefix: /v1/screener                        ; required: growth
  - prefix: /v1/exposure/summary/               ; required: growth
  - prefix: /v1/exposure/zero-dte/              ; required: growth
  - prefix: /v1/volatility/                     ; required: growth
  - prefix: /v1/exposure/dex/                   ; required: basic
  - prefix: /v1/exposure/vex/                   ; required: basic
  - prefix: /v1/exposure/chex/                  ; required: basic
  - prefix: /v1/maxpain/                        ; required: basic
  - prefix: /v1/exposure/gex/                   ; required: free
  - prefix: /v1/exposure/levels/                ; required: free
  - prefix: /stockquote/                        ; required: free
# Index/ETF symbol gating + 0DTE grandfather rules live in `symbol_gates` and
# `endpoint_gates` blocks (omitted here; see full file). Layer 4 asserts the
# notebook's tier covers the highest-required endpoint it uses.
```

**Drift management:**

- `scripts/sync_tier_map.py` parses [EndpointAccessMiddleware.cs](../../../flashalpha-api/FlashAlpha.Api/Middleware/EndpointAccessMiddleware.cs) when run locally and regenerates the YAML
- `on-api-release.yml` triggers a workflow that runs the sync script and opens a drift PR if the YAML changes
- v1.1 will add empirical per-tier probing when CI provisions four dedicated tier keys

### Layer 5 — Production funnel sanity (weekly)

- Headless-Chrome render of each notebook's signup URL; assert `utm_*` params land in the rendered analytics tag
- Full uncached lychee link sweep
- Stars/clones/referrers report posted to Slack

## 8. CI workflows

| Workflow | Trigger | Layers | Target time |
|---|---|---|---|
| **pr.yml** | PR; push to non-main | 0, 1, 2-cassette, 4 | < 3 min |
| **nightly.yml** | schedule 03:00 UTC; workflow_dispatch | 2-live, 3, drift-PR opener | ~15 min |
| **weekly.yml** | schedule Mon 09:00 UTC | 5 | ~10 min |
| **on-sdk-release.yml** | `repository_dispatch` from `flashalpha-{python,js,go,dotnet,java}` on tag push | bump SDK in requirements.txt; rerun nightly suite; open issue on regression | ~15 min |
| **on-api-release.yml** | `repository_dispatch` from MC deploy pipeline | rerun nightly suite live; run sync_tier_map; PR on tier-map drift | ~15 min |

Python matrix: 3.10, 3.11, 3.12, 3.13 (matches existing CI). Ubuntu only.

**Secrets required:**

- `FLASHALPHA_API_KEY` — dedicated low-quota Alpha CI account
- `COOKBOOK_DISPATCH_PAT` — installed on the 5 SDK repos and MC deploy pipeline to send `repository_dispatch` into `flashalpha-examples`
- `SLACK_FUNNEL_WEBHOOK` — for weekly stats post

## 9. Migration map: existing 11 → cookbook slots

| Existing file | New location | Action |
|---|---|---|
| `01_quick_start.py` | `tier-a-hooks/05-bsm-greeks-one-call` | port + minimal-ize to "15 greeks in one call" |
| `02_gex_dashboard.py` | `tier-a-hooks/01-gex-dashboard` | port + Colab badge + screenshot — **canonical Phase-0 template** |
| `03_iv_rank_scanner.py` | `tier-e-flow/utility-iv-rank-scanner` | port — keep as non-numbered utility (doesn't fit "unusual flow" theme) |
| `04_vol_surface_3d.py` | `tier-a-hooks/03-3d-vol-surface-svi` | port + SVI overlay |
| `05_dealer_positioning.py` | `tier-b-dealer-flow/08-positioning-regime-classifier` | port + classifier output |
| `06_kelly_sizing.py` | `tier-b-dealer-flow/utility-kelly-sizing` | keep as supporting utility |
| `07_zero_dte_analytics.py` | `tier-d-0dte/21-pin-risk-scanner` | port |
| `08_advanced_volatility.py` | `tier-c-vol-surface/15-svi-time-series-spx` | port + time series |
| `09_volatility_analysis.py` | `tier-c-vol-surface/18-skew-dynamics-fomc` | port + event overlay |
| `10_live_options_screener.py` | `tier-e-flow/24-uoa-scanner-150-lines` | port + align with the UOA article |
| `11_max_pain_analysis.py` | `tier-a-hooks/06-why-spx-pins-max-pain` | port |

**Counting:**

- 33 numbered slots in the plan (A:7 + B:7 + C:6 + D:3 + E:3 + F:4 + G:3)
- 9 of the 11 existing scripts fill numbered slots (1 in A:01,03,05,06; B:08; C:15,18; D:21; E:24)
- 2 existing scripts (`06_kelly_sizing`, `03_iv_rank_scanner`) become non-numbered utilities
- **24 net-new numbered recipes to author**
- v1.0 ships 30 numbered (hold 3 in reserve) + 2 utilities = **32 recipes total**

### 9.1 Net-new authoring queue (in ship order)

- **Tier A (3 net-new):** `02-gamma-flip-cross-index`, `04-call-wall-put-wall-explorer`, `07-daily-gamma-flip-slack-bot`
- **Tier B (6 net-new):** `09-intraday-dealer-hedging-flow`, `10-pin-risk-monitor-0dte`, `11-spotgamma-killer-dashboard` (Streamlit, deployed to dash.flashalpha.com), `12-cross-symbol-dealer-leaderboard`, `13-charm-decay-map`, `14-vanna-trap-detector`
- **Tier C (4 net-new):** `16-vrp-harvest-leak-free-backtest` (Alpha conversion notebook), `17-variance-swap-pricing`, `19-realtime-butterfly-arb-detector`, `20-term-structure-zscore`
- **Tier D (2 net-new):** `22-expected-move-shrinkage-tracker`, `23-0dte-gamma-acceleration-alert`
- **Tier E (2 net-new):** `25-sweep-vs-block-classifier`, `26-opening-bias-position-building`
- **Tier F (4 net-new):** `27-gex-flip-reversal-backtest`, `28-event-study-opex`, `29-replay-covid-march-2020`, `30-walkforward-0dte-optimization`
- **Tier G (3 net-new):** `31-fastapi-proxy-for-team`, `32-postgres-daily-ingest`, `33-discord-bot-daily-levels`

## 10. Phased ship (solo author, 51 days)

| Phase | Days | Deliverable |
|---|---|---|
| **0 — Foundation** | 3 | jupytext, pre-commit, Layer 0+1 tests, frontmatter pydantic schema, CTA renderer, `scripts/new_recipe.py`, `endpoint_tiers.yaml` v1 (manually extracted from middleware), CI `pr.yml`. Port `02_gex_dashboard.py → tier-a-hooks/01-gex-dashboard` end-to-end as canonical template. CI green. |
| **1 — Migrate existing 11** | 5 | Port all 11 existing scripts to paired form in tier subdirs. Layer 0/1/2-cassette green per recipe. |
| **2 — Tier A complete + launch v0.1** | 4 | 3 net-new Tier A. Layer 4 wired up. Coordinated launch: X thread, awesome-quant + awesome-finance + awesome-python PRs, HN Show, Discord. |
| **3 — Tier B + dash.flashalpha.com** | 11 | 6 net-new Tier B. Streamlit dashboard for #11 deployed to dash.flashalpha.com (subdomain reservation + container deploy adds ~2 days vs HF Spaces). |
| **4 — Tier C vol-surface** | 7 | 4 net-new. #16 is the Alpha-conversion notebook. Layer 4 stress-tested. |
| **5 — Tier D + E** | 5 | 4 net-new combined. |
| **6 — Tier F backtests** | 9 | 4 net-new. Layer 3 golden snapshots wired up. Every backtest produces a publishable equity-curve screenshot. |
| **7 — Tier G engineering** | 4 | 3 net-new. |
| **8 — Polish + v1.0 launch** | 3 | HN Show #2, newsletter outreach (5 quant newsletters), llms.txt update, cross-link sweep from MC concept pages. |

**Total: 51 working days solo** (~10–11 weeks at 5 days/week).

## 11. Risk register

| Risk | Mitigation |
|---|---|
| API key leaks in committed cell outputs | Layer 0 gitleaks + scrub_outputs.py + Layer 1 regex; CI key is a dedicated low-quota Alpha account so blast radius is bounded |
| API drift breaks cookbook silently | Nightly Layer 2-live + auto-opened drift PRs |
| SDK breaking change orphans recipes | `on-sdk-release.yml` fires on every SDK tag |
| Tier map drift (endpoint moves Free → Alpha undetected) | `on-api-release.yml` runs `sync_tier_map.py` and opens drift PR; v1.1 adds empirical per-tier probing |
| Runaway CI quota burn | per-recipe `max_api_calls` budget; dedicated CI key with hard rate limit |
| Notebook rot (stale "as-of" charts) | `last_validated_live` updated nightly; recipes >30 days stale flagged in weekly report |
| `imagehash` flapping on matplotlib bumps | Pin matplotlib to minor version; explicit bump + snapshot re-approval |
| `.ipynb` JSON merge conflicts | jupytext makes `.py` the authoritative diff target; `.ipynb` rarely conflicts because authors don't edit it directly |
| Author-time blowout (51 days) | Layer 0+1 + `scripts/new_recipe.py` keep each net-new recipe at ~2–3 h once template is solid |
| One-Alpha-key limitation hides tier bugs | Static Layer 4 + `sync_tier_map.py` is best-effort; v1.1 four-key empirical probing closes the gap |

## 12. Phase-0 deliverable definition of done

Phase 0 ships when all of the following are true:

1. `pre-commit run --all-files` passes with the new hooks
2. `pytest tests/test_layer0_secrets.py tests/test_layer1_structural.py` passes (one recipe present)
3. `pytest tests/test_layer2_execution.py` passes against the cassette for `01-gex-dashboard`
4. `pytest tests/test_layer4_tier_static.py` passes (one recipe + `endpoint_tiers.yaml`)
5. CI workflow `pr.yml` green on a clean PR
6. `scripts/new_recipe.py --slug demo-99 --tier free` produces a valid pair that passes Layers 0/1
7. `notebooks/tier-a-hooks/01-gex-dashboard.{py,ipynb}` is the canonical template — every later recipe is a copy-and-modify of this

Phase 0 is the only phase that requires green-fielding test infra. Phase 1+ is repetitive mechanical authoring.

## 13. Open items (deferred, not blockers)

- **v1.1 per-tier probing**: provision 4 CI accounts (Free / Basic / Growth / Alpha); add empirical Layer 4 matrix.
- **Binder support**: skipped for v1.0 (Colab covers the need). Reconsider if Binder discovery proves to drive traffic.
- **JS/Go/.NET/Java cookbook ports**: out of scope for v1.0. The five other SDKs can ship their own cookbook repos later, gated on Python cookbook conversion data.
- **MCP integration recipes**: stay scoped to `flashalpha-mcp`; cookbook links to MCP docs from the bottom CTA only.
