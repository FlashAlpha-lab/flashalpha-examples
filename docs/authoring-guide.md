# Authoring a cookbook recipe

A 10-minute walkthrough. For deeper architectural context see
[the spec](superpowers/specs/2026-05-25-flashalpha-cookbook-design.md).
For the canonical field reference see [frontmatter-schema.md](frontmatter-schema.md).

## Prerequisites

```bash
git clone https://github.com/FlashAlpha-lab/flashalpha-examples
cd flashalpha-examples
python -m pip install -e ".[dev]"
pre-commit install
export FLASHALPHA_API_KEY=fa_your_key
```

The dev install pulls everything you need: `jupytext`, `papermill`,
`vcrpy`, `nbformat`, `ruff`, `gitleaks`. The `pre-commit install` wires
the redaction + sync + lint hooks so you cannot accidentally commit a
broken or leaky notebook.

## The five-step workflow

### 1. Scaffold the pair

```bash
python -m scripts.new_recipe \
  --slug 02-gamma-flip-cross-index \
  --title "Find Today's Gamma Flip Across Indexes" \
  --tier free \
  --tier-dir tier-a-hooks
```

Writes a paired `.py` + `.ipynb` at `notebooks/tier-a-hooks/02-gamma-flip-cross-index.{py,ipynb}`.
The pair is pre-filled with the correct frontmatter, the top CTA cell,
a starter code cell, and the bottom CTA cell. **You should not edit the
CTA cells** — Layer 1 will fail the build if their content drifts from
what `cookbook_tools.cta_template` would render.

CLI flags:

| Flag | Required | Description |
|---|---|---|
| `--slug` | yes | Kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`). Becomes the filename. |
| `--title` | yes | H1 title of the recipe. |
| `--tier` | yes | One of `free`, `basic`, `growth`, `alpha`. |
| `--tier-dir` | yes | Tier directory under `notebooks/`. See "Choosing the tier directory" below. |
| `--out-root` | no | Repo root (defaults to CWD). Useful when testing in `tmp_path`. |
| `--runtime-budget` | no | Default 60s. Will be enforced by Layer 2. |
| `--max-api-calls` | no | Default 8. Will be enforced by Layer 2. |
| `--sdk-version-min` | no | Default `1.0.1`. |

#### Choosing the tier directory

Recipes are organized by topic, not by tier requirement:

| Directory | Topic |
|---|---|
| `tier-a-hooks/` | Short attention-grabbers — GEX dashboards, vol surfaces, max pain |
| `tier-b-dealer-flow/` | Dealer positioning deep-dives |
| `tier-c-vol-surface/` | SVI, VRP, variance swaps, skew dynamics |
| `tier-d-0dte/` | Same-day expiry analytics |
| `tier-e-flow/` | Unusual flow scanners |
| `tier-f-backtest/` | Historical replay backtests (use locked `at=` timestamps) |
| `tier-g-engineering/` | Engineering glue — FastAPI proxy, Postgres ingest, Discord bots |

The "tier" in the directory name is the **topic tier from the spec**,
not the subscription tier. A `tier-a-hooks/` recipe can require any
subscription tier — though most should target `free`.

### 2. Fill in the body

Open `notebooks/tier-a-hooks/02-gamma-flip-cross-index.py` in your
editor. The scaffold's code cell looks like:

```python
import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])
# TODO: implement recipe body here.
```

Replace the TODO with the recipe code. The pair is configured so that
**editing the `.py` file** is your day-to-day workflow — `jupytext` syncs
to the `.ipynb` automatically on save (if your editor has the jupytext
plugin) or on pre-commit.

**Critical rules** for the code cells:

1. **Never hardcode an API key.** Use `os.environ["FLASHALPHA_API_KEY"]`.
2. **Never `except: pass`** or any except that doesn't `raise` or call a
   `logger.error/exception/critical`. Layer 1 fails on silent swallowing.
3. **Never use `%%capture`.** It suppresses traceback. Banned by Layer 1.
4. **List every imported package** that isn't in `requirements.txt`
   (matplotlib, numpy, flashalpha are already there). Layer 1 enforces.
5. **Mark every API endpoint** the recipe calls in `endpoints_used` in
   the frontmatter. Layer 4 + the cassette-cross-validation test fail
   if a recipe calls an undeclared endpoint.
6. **Use `matplotlib.use("Agg")`** before importing pyplot — keeps the
   recipe headless-safe for Colab / CI.

### 3. Execute against live API + record the cassette

```bash
# Re-execute to populate cell outputs (chart, prints, DataFrames).
python -m papermill \
  notebooks/tier-a-hooks/02-gamma-flip-cross-index.ipynb \
  notebooks/tier-a-hooks/02-gamma-flip-cross-index.ipynb \
  --kernel python3

# Record vcrpy cassette for Layer 2 replay.
python -m scripts.record_cassettes \
  notebooks/tier-a-hooks/02-gamma-flip-cross-index.ipynb

# Scrub auth headers from outputs (defensive — usually a no-op).
python -m scripts.scrub_outputs \
  notebooks/tier-a-hooks/02-gamma-flip-cross-index.ipynb
```

The cassette lands at
`tests/cassettes/02-gamma-flip-cross-index/cassette.yaml`. vcrpy strips
`Authorization`, `X-Api-Key`, and `Cookie` headers from requests as it
records, so the committed cassette is safe to make public.

### 4. Run the test suite

```bash
pytest
```

You should see your recipe parametrized into Layers 0/1/2/4 plus the
cassette-integrity and endpoints-match-cassette tests — typically 8-9
new green tests. If anything fails, the failure messages tell you which
invariant broke.

Most common failure modes:

| Failure | Cause | Fix |
|---|---|---|
| `top CTA cell content mismatch` | You edited the auto-generated CTA cell | Restore from `render_top_cell(fm, tier_dir=...)` output, or rerun the scaffolder and copy the body cell back |
| `imports X but it is not in requirements.txt` | Used a package not declared | Add to `requirements.txt` AND `pyproject.toml [project].dependencies` |
| `cassette has calls not in endpoints_used` | Recipe hits an undeclared endpoint | Add it to `endpoints_used` in the frontmatter |
| `<recipe> took N.Ns, exceeds runtime_budget_seconds` | Recipe is slow under replay | Bump `runtime_budget_seconds` in frontmatter; if you can't make it fit in 60s, the recipe is probably too ambitious for a single notebook |
| `cell N declared in tier_gated_cells but endpoint X requires only Y` | A gated cell isn't actually gated | Drop the index from `tier_gated_cells` |

### 5. Commit

```bash
git add notebooks/tier-a-hooks/02-gamma-flip-cross-index.{py,ipynb} \
        tests/cassettes/02-gamma-flip-cross-index/cassette.yaml
git commit -m "Add recipe: gamma flip across indexes"
git push
```

Pre-commit runs gitleaks + scrub + jupytext sync + nbqa-ruff + ruff. If
any modify a file, the commit aborts and shows you the diff. Restage
and commit again.

CI (Python 3.10-3.13 matrix) runs the full test suite on push. Should
match what you saw locally.

## Recipe patterns

### A free-tier recipe

Minimal frontmatter:

```yaml
tier: free
endpoints_used:
  - /v1/exposure/gex/{symbol}
  - /v1/exposure/levels/{symbol}
tier_gated_cells: []
```

Recipes that target `tier: free` should use only the endpoints listed
in the "Catch-all free-tier endpoints" section of
[`endpoint_tiers.yaml`](../endpoint_tiers.yaml). The Layer 4 test will
catch mismatches.

### A recipe that *intentionally* hits a higher tier (Alpha)

If a recipe is structured "free 80% / Alpha 20%" — where the free cells
let everyone learn something useful, and the last cell shows an
Alpha-only call as an upgrade prompt — declare the higher cell explicitly:

```yaml
tier: growth                     # what most cells need
tier_gated_cells: [7]            # 0-indexed cell that calls an Alpha endpoint
```

The scaffolder won't generate the gate cell for you (that's by design —
the recipe author writes the prose explaining why this cell needs an
upgrade). You write the markdown gate cell immediately before cell 7
using:

```python
from cookbook_tools.cta_template import render_gate_cell
from cookbook_tools.frontmatter import Frontmatter
# ... build fm ...
print(render_gate_cell(endpoint="/v1/vrp/SPY", required_tier="alpha", fm=fm))
```

Copy the output into a markdown cell at index 6 (immediately before the
gated code cell). Layer 1 enforces that the gate cell precedes the
tier-gated code cell and that its content matches `render_gate_cell`'s
output exactly.

### A deterministic backtest recipe (Phase 6+)

Backtest recipes use historical replay with a locked `at=` timestamp so
their outputs are identical on every run. Declare expected artifacts:

```yaml
expected_artifacts:
  dataframes: [equity_curve, drawdown]
  charts: [equity_curve.png]
```

Phase 6 will add the Layer 3 golden-snapshot tests that compare these
against `snapshots/<slug>/`. Until then the fields are documentation-only.

## Topics off this guide

- **Cassette drift** — If a recipe's cassette stops matching reality
  (API field renamed, e.g.), the nightly job logs a `::notice::` with
  the diff. Refresh by re-running step 3 and committing.
- **Bumping the SDK** — Bump `sdk_version_min` in the frontmatter; Phase
  1+ adds the SDK-release dispatch workflow that re-validates.
- **Property tests** — Hypothesis covers the frontmatter parser and CTA
  renderer. If you add a new helper function, add property tests in
  `tests/cookbook_tools/test_*_properties.py`.

## See also

- [Frontmatter schema reference](frontmatter-schema.md) — every field with type + description
- [Design spec](superpowers/specs/2026-05-25-flashalpha-cookbook-design.md) — architectural decisions, test pyramid, phased ship plan
- [Phase 0 plan](superpowers/plans/2026-05-25-flashalpha-cookbook-phase0.md) — task-by-task implementation notes
- [endpoint_tiers.yaml](../endpoint_tiers.yaml) — which tier each endpoint requires
