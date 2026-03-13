# # Kelly Criterion for Options Sizing
#
# The Kelly Criterion gives the theoretically optimal fraction of capital to risk
# on a bet. FlashAlpha's fa.kelly() applies it to options, accounting for the
# full BSM return distribution.
#
# Workflow:
#   1. Get theoretical greeks to understand the option's risk profile.
#   2. Solve for implied vol from a market price.
#   3. Run Kelly sizing at different expected return (mu) assumptions.
#
# Requires: pip install flashalpha

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

SPOT    = 580.0   # SPY spot price
STRIKE  = 585.0   # slightly OTM call
DTE     = 14      # days to expiration
SIGMA   = 0.18    # assumed vol (annualized)
PREMIUM = 4.50    # market premium you'd pay
TYPE    = "call"

# --- Step 1: BSM greeks at assumed vol ---
greeks = fa.greeks(spot=SPOT, strike=STRIKE, dte=DTE, sigma=SIGMA, type=TYPE)
fo = greeks["first_order"]
so = greeks.get("second_order") or {}
print(f"=== BSM Greeks  (spot={SPOT}, strike={STRIKE}, DTE={DTE}, sigma={SIGMA*100:.0f}%) ===")
print(f"  Delta : {fo['delta']:.4f}")
print(f"  Gamma : {fo['gamma']:.6f}")
print(f"  Theta : {fo['theta']:.4f}  (per day)")
print(f"  Vega  : {fo['vega']:.4f}  (per 1% IV move)")

# --- Step 2: Implied vol from market premium ---
iv_result = fa.iv(spot=SPOT, strike=STRIKE, dte=DTE, price=PREMIUM, type=TYPE)
iv = iv_result["implied_volatility"]
print(f"\n=== Implied Vol from market premium ${PREMIUM} ===")
print(f"  IV = {iv*100:.2f}%")
print(f"  {'IV > assumed sigma — option is rich (sell candidate)' if iv > SIGMA else 'IV < assumed sigma — option is cheap (buy candidate)'}")

# --- Step 3: Kelly sizing across mu assumptions ---
print(f"\n=== Kelly Fraction vs Expected Daily Return (mu) ===")
print(f"  {'mu (daily)':>12}  {'Kelly fraction':>15}  {'Meaning'}")
print(f"  {'-'*55}")

MU_SCENARIOS = [0.0005, 0.001, 0.002, 0.005, 0.01]
for mu in MU_SCENARIOS:
    k = fa.kelly(spot=SPOT, strike=STRIKE, dte=DTE, sigma=iv, premium=PREMIUM, mu=mu, type=TYPE)
    frac = k.get("kelly_fraction") or k.get("fraction") or k.get("f")
    if frac is None:
        print(f"  {mu:>12.4f}  {'n/a':>15}  (check API response keys)")
        continue
    pct  = frac * 100
    note = "do not trade" if frac <= 0 else f"risk {pct:.1f}% of capital"
    print(f"  {mu:>12.4f}  {frac:>15.4f}  {note}")

print("""
--- What Kelly fraction means ---
  Fraction <= 0  : expected value is negative — do not trade.
  Fraction  0-1  : risk that fraction of capital on this position.
  Fraction  > 1  : mathematically optimal to use leverage (use with caution).

Kelly maximizes the long-run geometric growth rate of your portfolio.
In practice, half-Kelly (fraction / 2) is common to reduce drawdown volatility.
""")
