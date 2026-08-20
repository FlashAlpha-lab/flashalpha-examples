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

See [docs/superpowers/specs/2026-05-25-flashalpha-cookbook-design.md](docs/superpowers/specs/2026-05-25-flashalpha-cookbook-design.md) for the full spec.

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

## What the API covers

Recipes can call the full FlashAlpha endpoint surface. Beyond the core exposure
analytics (`/v1/exposure/gex|dex|vex|chex|summary|levels|narrative`, max pain,
SVI surfaces, VRP, 0DTE exposure, and the live/recent/blocks flow feeds), recent
endpoint families include:

- **Strategy Signals** (`/v1/strategies/*`) — 10 systematic signals
  (flow-anomaly, expiry-positioning, zero-dte, dealer-regime, vol-carry,
  yield-enhancement, surface-anomaly, skew, term-structure, tail-pricing) behind
  one uniform decision envelope, for trade selection and signal backtesting.
- **Earnings analytics** (`/v1/earnings/*`) — calendar, expected-move, history,
  iv-crush, earnings VRP, dealer-positioning, strategies, and a screener.
- **Structures** (`POST /v1/structures/pnl`, `POST /v1/structures/greeks`) —
  payoff curves and aggregate Greeks for arbitrary multi-leg structures.
- **Zero-DTE Flow** (`/v1/flow/zero-dte/snapshot|series|hedge-flow|heatmap|strike-flow`)
  — intraday dealer-hedging and signed-flow analytics.
- **Extended exposure** (`/v1/exposure/sheet|term-structure|basket|oi-diff`) —
  per-strike sheets, exposure across expiries, basket/portfolio exposure, and
  open-interest deltas.
- **Volatility extras** — `/v1/surface/svi`, `/v1/volatility/skew-term`,
  `/v1/volatility/spot-vol-correlation`,
  `/v1/volatility/realized` (Alpha+, range-based realized vol estimators:
  close-to-close, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang over
  rv10/rv20/rv30 windows),
  `/v1/volatility/forecast` (Alpha+, conditional vol forecasts via EWMA,
  HAR-RV, and GARCH(1,1) MLE), `/v1/dispersion`, `/v1/expected-move`,
  `/v1/liquidity`.
- **Macro / universe** — `/v1/macro/vix-state`, `/v1/universe`,
  `/v1/screener/fields`, plus `/v1/flow/options/{symbol}/dealer-premium`,
  `/v1/flow/stocks/{symbol}/bars`, and `/v1/vrp/{symbol}/history`.

Tier requirements for every endpoint live in [endpoint_tiers.yaml](endpoint_tiers.yaml);
full request/response shapes are documented at the
[FlashAlpha API reference](https://lab.flashalpha.com/llms.txt).

## Futures (CME)

FlashAlpha serves the full options-analytics stack for **CME futures** across six complexes - equity index (`ES=F`, `NQ=F`, `RTY=F`, `YM=F`, `MES=F`, `MNQ=F`), metals (`GC=F` gold, `SI=F` silver), energy (`CL=F` crude oil, `NG=F` natural gas), the Treasury curve (`ZT=F`, `ZF=F`, `ZN=F`, `TN=F`, `ZB=F`, `UB=F`), grains (`ZC=F` corn, `ZS=F` soybeans, `ZW=F` wheat) and crypto (`BTC=F` bitcoin). Options-on-futures are priced with **Black-76** (forward-priced) and each root carries its own CME contract multiplier, so notionals and dollar gamma are in real dollars. Note the quote conventions: Treasuries are quoted in points of par and grains in cents, so their multipliers are the contract size divided by 100. Everything that works for an equity works for futures: gamma exposure (GEX), DEX, VEX, CHEX, key levels, max pain, the IV surface, exposure summary, narrative, and live flow.

```bash
# Gamma exposure for the E-mini S&P 500 future (note the %3D-encoded '=')
curl -H "X-Api-Key: $FLASHALPHA_API_KEY" \
  "https://lab.flashalpha.com/v1/exposure/gex/ES%3DF"
```

Use the `=F` suffix - bare `ES`/`NQ` are equities, not futures. In raw REST paths URL-encode the `=` as `%3D` (e.g. `GET /v1/exposure/gex/GC%3DF`); SDK methods take the plain string `"GC=F"`. Futures symbols require the Growth plan or higher. Historical replay for futures is coming; live analytics are available now.

## License

MIT. See [LICENSE](LICENSE).

## What the paid tiers unlock

The free tier covers single-expiry GEX on equities, key levels, the BSM Greeks/IV
calculator and stock quotes. Paid tiers add:

- **DEX, VEX (vanna) and CHEX (charm) exposure, plus max pain** — from the **Basic
  tier** ($79/mo), with ETF and index symbols.
- **Full-chain GEX, 0DTE and flow analytics** — from the **Growth tier** ($299/mo).
- **Point-in-time replay since 2017, SVI vol surfaces, VRP analytics, higher-order
  Greeks**, uncached and unlimited — the **Alpha tier** ($1,499/mo). FlashAlpha is one
  of the only public APIs publishing aggregate vanna and charm exposure across the
  full universe, with no look-ahead and no training-serving skew.

Built for quants, prop desks, and vol funds. See the full picture and get a key:
**[flashalpha.com/for-quant-teams](https://flashalpha.com/for-quant-teams?utm_source=github&utm_medium=readme&utm_campaign=repo-flashalpha-examples)**
