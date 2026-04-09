# # Max Pain Analysis — dealer alignment, pain curve, and pin probability
#
# The Max Pain endpoint returns the strike where total option holder payout is
# minimized. This analysis overlays dealer positioning (gamma flip, call/put
# walls) to identify whether max pain acts as a convergence magnet or is
# overridden by directional gamma flow.
#
# Docs: https://flashalpha.com/docs
# Install: pip install "flashalpha>=0.3.2"
#
# Tier: Growth+ required

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# ---------------------------------------------------------------------------
# 1) Full-chain max pain (all expirations)
# ---------------------------------------------------------------------------
result = fa.max_pain("SPY")
print(f"Max pain strike: {result['max_pain_strike']}")
print(f"Spot: {result['underlying_price']}")
print(f"Distance: {result['distance']['absolute']:.2f} ({result['distance']['percent']:.2f}%) {result['distance']['direction']}")
print(f"Signal: {result['signal']}")
print(f"Pin probability: {result['pin_probability']}/100")

# ---------------------------------------------------------------------------
# 2) Dealer alignment overlay
# ---------------------------------------------------------------------------
da = result["dealer_alignment"]
print(f"\nDealer alignment: {da['alignment']}")
print(f"  {da['description']}")
print(f"  Gamma flip: {da['gamma_flip']}")
print(f"  Call wall: {da['call_wall']}")
print(f"  Put wall: {da['put_wall']}")
print(f"  Regime: {result['regime']}")

# ---------------------------------------------------------------------------
# 3) Expected move context
# ---------------------------------------------------------------------------
em = result["expected_move"]
print(f"\nATM straddle: ${em['straddle_price']:.2f}")
print(f"ATM IV: {em['atm_iv']}%")
print(f"Max pain within expected range: {em['max_pain_within_expected_range']}")

# ---------------------------------------------------------------------------
# 4) Pain curve — top 5 strikes by lowest total pain
# ---------------------------------------------------------------------------
curve = sorted(result["pain_curve"], key=lambda x: x["total_pain"])
print("\nPain curve (lowest pain strikes):")
for row in curve[:5]:
    print(f"  {row['strike']:>8}  call_pain=${row['call_pain']:>12,.0f}  put_pain=${row['put_pain']:>12,.0f}  total=${row['total_pain']:>12,.0f}")

# ---------------------------------------------------------------------------
# 5) OI distribution around max pain
# ---------------------------------------------------------------------------
mp = result["max_pain_strike"]
oi_near = [s for s in result["oi_by_strike"] if abs(s["strike"] - mp) <= 10]
print(f"\nOI near max pain ({mp}):")
for s in oi_near[:5]:
    print(f"  {s['strike']:>8}  call_oi={s['call_oi']:>8,}  put_oi={s['put_oi']:>8,}  total={s['total_oi']:>8,}")

print(f"\nPut/call OI ratio: {result['put_call_oi_ratio']:.3f}")

# ---------------------------------------------------------------------------
# 6) Multi-expiry calendar
# ---------------------------------------------------------------------------
if result.get("max_pain_by_expiration"):
    print("\nMax pain by expiry:")
    for entry in result["max_pain_by_expiration"][:5]:
        print(f"  {entry['expiration']}  strike={entry['max_pain_strike']}  DTE={entry['dte']}  OI={entry['total_oi']:,}")

# ---------------------------------------------------------------------------
# 7) Single-expiry max pain
# ---------------------------------------------------------------------------
# Get first available expiration
opts = fa.options("SPY")
if opts.get("expirations"):
    exp = opts["expirations"][0]["expiration"]
    single = fa.max_pain("SPY", expiration=exp)
    print(f"\nMax pain for {exp}: {single['max_pain_strike']}")
    print(f"  Pin probability: {single['pin_probability']}/100")
    print(f"  Dealer alignment: {single['dealer_alignment']['alignment']}")
