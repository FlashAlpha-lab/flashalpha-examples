# # Advanced Volatility Analytics: SVI, Variance Surface, Arbitrage Detection
#
# fa.adv_volatility() surfaces the quantitative plumbing beneath the options market.
# It returns:
#
#   svi_parameters   — Stochastic Volatility Inspired (SVI) fit per expiration.
#                      SVI gives a parsimonious 5-parameter model of the vol smile
#                      that is free of static arbitrage by construction.
#
#   variance_surface — Total implied variance (sigma^2 * T) across strike and tenor,
#                      the natural coordinate for variance swap pricing and model
#                      calibration. Variance is additive; IV is not.
#
#   arbitrage_flags  — Calendar spread arbitrage and butterfly (convexity) arbitrage
#                      violations detected in the raw market surface.
#
#   greeks_surfaces  — Delta, gamma, vanna, and vomma surfaces across all strikes
#                      and expirations — useful for aggregate exposure maps.
#
#   variance_swap    — Fair value variance swap rates (realized vs implied variance)
#                      per tenor. Variance swaps pay the difference between realized
#                      and implied variance; the rate is the break-even vol squared.
#
# Requires: pip install flashalpha

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

SYMBOL = "SPY"

# --- Fetch advanced volatility data ---
data = fa.adv_volatility(SYMBOL)

print(f"=== Advanced Volatility Analytics: {SYMBOL} ===\n")

# --- SVI parameters ---
# Each expiration has its own SVI fit: a, b, rho, m, sigma
#   a     : overall variance level (vertical shift)
#   b     : angle between left and right asymptotes
#   rho   : skew / correlation between spot and vol
#   m     : translation of the smile along log-moneyness
#   sigma : ATM curvature / smile width
svi_params = data.get("svi_parameters") or []
if svi_params:
    print("--- SVI Parameters by Expiration ---")
    print(f"  {'Expiry':<14} {'a':>8} {'b':>8} {'rho':>8} {'m':>8} {'sigma':>8}")
    print(f"  {'-'*54}")
    for row in svi_params[:8]:  # cap at 8 rows for readability
        exp   = row.get("expiration") or row.get("expiry") or "?"
        a     = row.get("a")
        b     = row.get("b")
        rho   = row.get("rho")
        m     = row.get("m")
        sigma = row.get("sigma")
        def fmt(v):
            return f"{v:.4f}" if v is not None else "n/a"
        print(f"  {str(exp):<14} {fmt(a):>8} {fmt(b):>8} {fmt(rho):>8} {fmt(m):>8} {fmt(sigma):>8}")
    if len(svi_params) > 8:
        print(f"  ... and {len(svi_params) - 8} more expirations")

# --- Variance surface ---
# Total variance = IV^2 * (DTE / 365). Unlike IV, variance is additive
# across time, making it the correct basis for calendar spread pricing.
variance_surface = data.get("variance_surface") or []
if variance_surface:
    print("\n--- Variance Surface (sample) ---")
    print(f"  {'Strike':>8} {'DTE':>6} {'Total Var':>12} {'IV (implied)':>14}")
    print(f"  {'-'*42}")
    for row in variance_surface[:10]:
        strike   = row.get("strike")
        dte      = row.get("dte")
        tot_var  = row.get("total_variance") or row.get("variance")
        iv       = (tot_var / (dte / 365)) ** 0.5 if tot_var and dte else None
        s_str    = f"{strike:.1f}"  if strike  is not None else "n/a"
        d_str    = f"{dte:.0f}"     if dte     is not None else "n/a"
        v_str    = f"{tot_var:.4f}" if tot_var is not None else "n/a"
        iv_str   = f"{iv*100:.2f}%" if iv      is not None else "n/a"
        print(f"  {s_str:>8} {d_str:>6} {v_str:>12} {iv_str:>14}")
    if len(variance_surface) > 10:
        print(f"  ... and {len(variance_surface) - 10} more points")

# --- Arbitrage flags ---
# Calendar arbitrage: total variance must increase monotonically with tenor.
# Butterfly arbitrage: the smile must be convex (no negative local variance).
# These flags identify strikes/expirations where the market is internally
# inconsistent — useful for model calibration quality control.
arb_flags = data.get("arbitrage_flags") or {}
print("\n--- Arbitrage Detection ---")
cal_viols  = arb_flags.get("calendar_violations") or []
bfly_viols = arb_flags.get("butterfly_violations") or []
cal_clean  = arb_flags.get("calendar_clean")
bfly_clean = arb_flags.get("butterfly_clean")

if cal_clean is not None:
    status = "CLEAN" if cal_clean else f"{len(cal_viols)} violation(s)"
    print(f"  Calendar spread arbitrage : {status}")
if bfly_clean is not None:
    status = "CLEAN" if bfly_clean else f"{len(bfly_viols)} violation(s)"
    print(f"  Butterfly (convexity)     : {status}")

for k, v in arb_flags.items():
    if k not in ("calendar_violations", "butterfly_violations",
                 "calendar_clean", "butterfly_clean"):
        print(f"  {k:<30} {v}")

if cal_viols:
    print(f"\n  Calendar violations (first 3):")
    for v in cal_viols[:3]:
        print(f"    {v}")
if bfly_viols:
    print(f"\n  Butterfly violations (first 3):")
    for v in bfly_viols[:3]:
        print(f"    {v}")

# --- Greeks surfaces ---
# Aggregate delta/gamma/vanna/vomma across all strikes and expirations.
# A positive aggregate vanna means dealers need to buy delta as vol rises.
greeks_surfaces = data.get("greeks_surfaces") or {}
print("\n--- Aggregate Greeks Surfaces ---")
for greek in ("delta", "gamma", "vanna", "vomma"):
    val = greeks_surfaces.get(f"net_{greek}") or greeks_surfaces.get(greek)
    if val is not None:
        print(f"  Net {greek:<10} : {val:,.2f}")
for k, v in greeks_surfaces.items():
    if not any(k.startswith(g) or k.endswith(g) for g in ("delta","gamma","vanna","vomma")):
        print(f"  {k:<30} {v}")

# --- Variance swap rates ---
# The variance swap rate is the strike at which a variance swap is fairly priced.
# It equals the risk-neutral expectation of realized variance over the tenor.
# Annualized: sqrt(variance_swap_rate) gives the break-even vol.
var_swap = data.get("variance_swap") or {}
print("\n--- Variance Swap Rates ---")
rates = var_swap.get("rates") or var_swap.get("tenors") or []
if rates:
    print(f"  {'Tenor':<10} {'Var Swap Rate':>15} {'Break-even Vol':>16}")
    print(f"  {'-'*43}")
    for row in rates:
        tenor   = row.get("tenor") or row.get("dte") or row.get("expiration")
        rate    = row.get("rate") or row.get("variance_swap_rate")
        bev     = rate ** 0.5 if rate is not None else None
        t_str   = str(tenor)   if tenor is not None else "n/a"
        r_str   = f"{rate:.6f}" if rate is not None else "n/a"
        b_str   = f"{bev*100:.2f}%" if bev is not None else "n/a"
        print(f"  {t_str:<10} {r_str:>15} {b_str:>16}")
else:
    for k, v in var_swap.items():
        print(f"  {k:<30} {v}")

print("""
--- Key concepts ---
  SVI fit       : a smooth, arbitrage-free parametric model of each expiry's smile.
  Total variance: IV^2 * T — additive across time, correct basis for replication.
  Arb flags     : any violations should be treated as data quality warnings.
  Vanna exposure: tells you how dealer delta will shift when IV moves.
  Var swap rate : equals the fair strike for a pure variance exposure (no vega path
                  dependency). Compare to realized vol to assess vol risk premium.
""")
