# # Understanding Dealer Positioning
#
# Dealers (market makers) must hedge their books continuously.
# GEX, DEX, VEX, and CHEX tell you *how* they hedge — which drives flows.
# Requires: pip install flashalpha

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

SYMBOL = "SPY"

# --- Exposure summary (Growth+ endpoint) ---
summary = fa.exposure_summary(SYMBOL)
exp     = summary["exposure"]

print(f"=== Dealer Exposure Summary: {SYMBOL} ===\n")

# Net aggregate exposures
for label, key in [
    ("Net GEX  (Gamma Exposure)", "net_gex"),
    ("Net DEX  (Delta Exposure)", "net_dex"),
    ("Net VEX  (Vanna Exposure)", "net_vex"),
    ("Net CHEX (Charm Exposure)", "net_chex"),
]:
    val = exp.get(key)
    print(f"  {label:<35} {val:>18,.0f}" if val is not None else f"  {label:<35} n/a")

# Hedging estimates
hedging = exp.get("hedging") or {}
print("\n--- Hedging Estimates ---")
for k, v in hedging.items():
    print(f"  {k:<30} {v}")

# Zero-DTE contribution
dte0 = exp.get("zero_dte") or {}
print("\n--- Zero-DTE Contribution ---")
for k, v in dte0.items():
    print(f"  {k:<30} {v}")

# --- Narrative / regime analysis (Growth+ endpoint) ---
print("\n--- Regime Narrative ---")
narrative_resp = fa.narrative(SYMBOL)
print(narrative_resp.get("narrative") or narrative_resp)
