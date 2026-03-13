# # Getting Started with FlashAlpha
#
# This notebook walks through the core FlashAlpha API in under 30 lines.
# Install: pip install flashalpha
# Docs: https://flashalpha.com/docs

import os
from flashalpha import FlashAlpha

# Initialize client — set FLASHALPHA_API_KEY in your environment
fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# --- GEX for SPY ---
gex = fa.gex("SPY")
print("GEX strikes (first 3):", gex["strikes"][:3])

# --- Key exposure levels ---
levels = fa.exposure_levels("SPY")
print("Gamma flip :", levels["levels"]["gamma_flip"])
print("Call wall  :", levels["levels"]["call_wall"])
print("Put wall   :", levels["levels"]["put_wall"])

# --- Live quote ---
quote = fa.stock_quote("SPY")
print(f"SPY  bid={quote['bid']}  ask={quote['ask']}  mid={quote['mid']}")

# --- BSM greeks ---
greeks = fa.greeks(spot=580, strike=585, dte=7, sigma=0.18, type="call")
fo = greeks["first_order"]
print(f"Delta={fo['delta']:.4f}  Gamma={fo['gamma']:.6f}  Theta={fo['theta']:.4f}  Vega={fo['vega']:.4f}")
