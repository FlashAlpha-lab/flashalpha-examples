# # 0DTE Intraday Analytics
#
# Same-day expiration options (0DTE) now account for the majority of SPY/QQQ
# options volume. This script pulls real-time 0DTE analytics from FlashAlpha
# and prints the key metrics traders watch every morning.
#
# What fa.zero_dte() returns:
#   regime        — whether dealers are net long or short 0DTE gamma
#   expected_move — market-implied intraday range (in points and percent)
#   pin_risk      — strikes where price is most likely to gravitate (max pain)
#   hedging       — estimated dealer hedge flows driven by 0DTE exposure
#   theta_decay   — aggregate theta burn profile across the 0DTE chain
#
# Requires: pip install flashalpha

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

SYMBOL = "SPY"

# --- Fetch 0DTE analytics ---
# strike_range limits which strikes are included (default: ATM +/- 5%)
data = fa.zero_dte(SYMBOL)

print(f"=== 0DTE Analytics: {SYMBOL} ===\n")

# --- Regime ---
# Positive 0DTE GEX -> dealers are long gamma -> they buy dips and sell rips,
# which pins price near expiration. Negative -> dealers amplify moves.
regime = data.get("regime") or {}
print("--- Regime ---")
for k, v in regime.items():
    print(f"  {k:<30} {v}")

# --- Expected move ---
# Derived from 0DTE option prices. This is the one-standard-deviation
# intraday range the market is pricing in as of now.
expected_move = data.get("expected_move") or {}
print("\n--- Expected Move (intraday, 1-sigma) ---")
em_pts = expected_move.get("points")
em_pct = expected_move.get("percent")
if em_pts is not None:
    print(f"  Points  : +/- {em_pts:.2f}")
if em_pct is not None:
    print(f"  Percent : +/- {em_pct*100:.2f}%")
for k, v in expected_move.items():
    if k not in ("points", "percent"):
        print(f"  {k:<30} {v}")

# --- Pin risk ---
# Strikes with the highest open interest act as gravitational anchors.
# Max pain is the price at which the most 0DTE premium expires worthless.
pin_risk = data.get("pin_risk") or {}
print("\n--- Pin Risk ---")
max_pain = pin_risk.get("max_pain")
if max_pain is not None:
    print(f"  Max pain strike : {max_pain}")
top_pins = pin_risk.get("top_strikes") or []
if top_pins:
    print(f"  Top pin strikes : {top_pins}")
for k, v in pin_risk.items():
    if k not in ("max_pain", "top_strikes"):
        print(f"  {k:<30} {v}")

# --- Hedging flows ---
# As 0DTE options approach expiration, their delta changes rapidly (gamma risk).
# These estimates show how many shares dealers must buy/sell to stay delta-neutral.
hedging = data.get("hedging") or {}
print("\n--- Estimated Dealer Hedging Flows ---")
for k, v in hedging.items():
    print(f"  {k:<30} {v}")

# --- Theta decay ---
# The aggregate daily theta burn for the 0DTE chain.
# This is the total premium at risk of decaying to zero by end of session.
theta_decay = data.get("theta_decay") or {}
print("\n--- Theta Decay Profile ---")
for k, v in theta_decay.items():
    print(f"  {k:<30} {v}")

# --- Interpretation guide ---
print("""
--- How to use this data ---
  Positive 0DTE regime  : price tends to pin near gamma-heavy strikes.
                          Sell strangles or iron condors near max pain.
  Negative 0DTE regime  : intraday moves can accelerate after a breakout.
                          Prefer directional strategies or long gamma.
  Expected move         : +/- range gives natural targets for the day.
  Pin risk strikes      : watch for price gravity around top pin strikes
                          in the final hour of trading.
  Theta decay           : premium sellers benefit as this number accrues
                          throughout the session.
""")
