# # Live Options Screener — filter & rank symbols in real time
#
# The Screener endpoint lets you filter and rank symbols across your tier's
# universe by any combination of stock, expiry, strike, or contract-level
# metrics: gamma exposure (GEX), VRP, implied volatility, greeks, harvest
# scores, dealer flow risk, and more. Data is live from an in-memory store,
# refreshed every 5-10 seconds.
#
# Docs: https://flashalpha.com/docs/lab-api-screener
# Cookbook: https://flashalpha.com/docs/lab-api-screener-cookbook
# Install: pip install "flashalpha>=0.3.0"
#
# Tier notes:
#   Growth — 10 symbols (SPY, QQQ, AAPL, TSLA, NVDA, AMZN, META, MSFT, SPX, AMD), 10 rows max
#   Alpha  — ~250 symbols, 50 rows max, formulas, harvest/dealer-flow-risk scores

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# ---------------------------------------------------------------------------
# 1) Simplest call — no filters, returns the default universe
# ---------------------------------------------------------------------------
result = fa.screener()
print(f"tier={result['meta']['tier']}  universe={result['meta']['universe_size']}")
for row in result["data"][:5]:
    print(f"  {row['symbol']:6}  price={row.get('price')}  regime={row.get('regime')}")

# ---------------------------------------------------------------------------
# 2) Positive-gamma names ranked by net GEX
# ---------------------------------------------------------------------------
result = fa.screener(
    filters={"field": "regime", "operator": "eq", "value": "positive_gamma"},
    sort=[{"field": "net_gex", "direction": "desc"}],
    select=["symbol", "price", "regime", "net_gex", "gamma_flip"],
)
print("\nPositive-gamma names:")
for row in result["data"]:
    print(f"  {row['symbol']:6}  net_gex={row['net_gex']:>15,.0f}  flip={row.get('gamma_flip')}")

# ---------------------------------------------------------------------------
# 3) Harvestable VRP setups (Alpha tier)
# ---------------------------------------------------------------------------
result = fa.screener(
    filters={
        "op": "and",
        "conditions": [
            {"field": "regime", "operator": "eq", "value": "positive_gamma"},
            {"field": "vrp_regime", "operator": "eq", "value": "harvestable"},
            {"field": "dealer_flow_risk", "operator": "lte", "value": 40},
            {"field": "harvest_score", "operator": "gte", "value": 65},
        ],
    },
    sort=[{"field": "harvest_score", "direction": "desc"}],
    select=["symbol", "price", "harvest_score", "dealer_flow_risk", "vrp_regime"],
)
print("\nHarvestable VRP setups:")
for row in result["data"]:
    print(
        f"  {row['symbol']:6}  harvest={row['harvest_score']:>3}  "
        f"risk={row['dealer_flow_risk']:>3}  vrp={row.get('vrp_regime')}"
    )

# ---------------------------------------------------------------------------
# 4) Vol scanner — where is IV rich vs realized?
# ---------------------------------------------------------------------------
result = fa.screener(
    filters={
        "op": "and",
        "conditions": [
            {"field": "vrp_20d", "operator": "gte", "value": 5},
            {"field": "atm_iv", "operator": "gte", "value": 25},
        ],
    },
    sort=[{"field": "vrp_20d", "direction": "desc"}],
    select=["symbol", "atm_iv", "rv_20d", "vrp_20d", "skew_25d"],
)
print("\nHigh VRP names (IV rich vs RV):")
for row in result["data"]:
    print(
        f"  {row['symbol']:6}  iv={row['atm_iv']:>5}  "
        f"rv={row['rv_20d']:>5}  vrp={row['vrp_20d']:>5}"
    )

# ---------------------------------------------------------------------------
# 5) Cascading filter — stock + expiry + strike + contract level
# ---------------------------------------------------------------------------
# Returns symbols with positive gamma, trimmed to expiries <= 14 days,
# high-OI strikes, and only the high-delta calls.
result = fa.screener(
    filters={
        "op": "and",
        "conditions": [
            {"field": "regime", "operator": "eq", "value": "positive_gamma"},
            {"field": "expiries.days_to_expiry", "operator": "lte", "value": 14},
            {"field": "strikes.call_oi", "operator": "gte", "value": 2000},
            {"field": "contracts.type", "operator": "eq", "value": "C"},
            {"field": "contracts.delta", "operator": "gte", "value": 0.3},
        ],
    },
    select=["symbol", "expiry_aggregates"],
    limit=10,
)
print("\nCascading filter (positive gamma, <=14 DTE, high-OI calls, delta>=0.3):")
for row in result["data"]:
    print(f"  {row['symbol']}: {len(row.get('expiry_aggregates', []))} expiries kept")

# ---------------------------------------------------------------------------
# 6) Custom formula — IV premium sorted descending (Alpha tier)
# ---------------------------------------------------------------------------
result = fa.screener(
    formulas=[{"alias": "iv_premium", "expression": "atm_iv - rv_20d"}],
    filters={"formula": "iv_premium", "operator": "gte", "value": 5},
    sort=[{"formula": "iv_premium", "direction": "desc"}],
    select=["symbol", "atm_iv", "rv_20d", "iv_premium"],
    limit=20,
)
print("\nCustom formula (iv_premium = atm_iv - rv_20d):")
for row in result["data"]:
    print(
        f"  {row['symbol']:6}  iv={row['atm_iv']:>5}  "
        f"rv={row['rv_20d']:>5}  premium={row['iv_premium']:>5}"
    )

# ---------------------------------------------------------------------------
# 7) Risk-adjusted harvest score (formula ranking)
# ---------------------------------------------------------------------------
result = fa.screener(
    formulas=[
        {"alias": "risk_adj", "expression": "harvest_score / (dealer_flow_risk + 1)"},
    ],
    filters={"field": "harvest_score", "operator": "gte", "value": 50},
    sort=[{"formula": "risk_adj", "direction": "desc"}],
    select=["symbol", "harvest_score", "dealer_flow_risk", "risk_adj"],
    limit=20,
)
print("\nRisk-adjusted harvest score (score / (risk + 1)):")
for row in result["data"]:
    print(
        f"  {row['symbol']:6}  score={row['harvest_score']:>3}  "
        f"risk={row['dealer_flow_risk']:>3}  risk_adj={row['risk_adj']:.3f}"
    )

# ---------------------------------------------------------------------------
# 8) Macro context filter — only show when VIX is elevated
# ---------------------------------------------------------------------------
result = fa.screener(
    filters={
        "op": "and",
        "conditions": [
            {"field": "regime", "operator": "eq", "value": "negative_gamma"},
            {"field": "vix", "operator": "gte", "value": 20},
        ],
    },
    select=["symbol", "regime", "atm_iv", "vix"],
)
print(f"\nNegative gamma names (VIX >= 20): {result['meta']['total_count']} found")
