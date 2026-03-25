# # Comprehensive Volatility Analysis
#
# fa.volatility() delivers a full-spectrum view of a ticker's volatility regime.
# Unlike fa.surface() which returns the raw IV grid, fa.volatility() synthesizes
# the surface into actionable analytics:
#
#   atm_iv            — current at-the-money implied volatility
#   iv_rank / iv_pct  — where current IV sits in its 52-week history
#   term_structure    — IV by expiration (contango vs backwardation)
#   skew              — put vs call skew (25-delta risk reversal)
#   vol_regime        — realized vs implied: is IV rich or cheap?
#   forward_vol       — implied forward volatility between tenors
#
# Example uses:
#   - Find overpriced options for premium selling (high IV rank)
#   - Detect vol regime shifts (IV crossing HV from below)
#   - Compare term structure across tickers for calendar spread ideas
#
# Requires: pip install flashalpha

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

SYMBOL = "TSLA"   # high-vol single stock — good for vol analysis

# --- Fetch comprehensive vol analytics ---
data = fa.volatility(SYMBOL)

print(f"=== Volatility Analysis: {SYMBOL} ===\n")

# --- ATM implied volatility ---
# The single most-watched vol number. ATM IV is the market's expectation of
# future realized vol over the option's life.
atm_iv = (
    data.get("atm_iv")
    or (data.get("volatility") or {}).get("atm_iv")
    or (data.get("summary") or {}).get("atm_iv")
)
if atm_iv is not None:
    print(f"ATM Implied Volatility : {atm_iv*100:.1f}%")

# --- IV rank and percentile ---
# IV rank (IVR): where current IV sits between its 52-week low and high.
#   IVR = (current - low) / (high - low)
#   IVR > 50 = IV elevated vs recent history -> premium selling favored.
# IV percentile (IVP): % of days in the past year where IV was lower.
vol_block = data.get("volatility") or data.get("vol") or data
iv_rank = vol_block.get("iv_rank") or vol_block.get("ivr") or data.get("iv_rank")
iv_pct  = vol_block.get("iv_percentile") or vol_block.get("ivp") or data.get("iv_percentile")
hv_30   = vol_block.get("hv30") or vol_block.get("realized_vol_30") or data.get("hv30")
hv_60   = vol_block.get("hv60") or vol_block.get("realized_vol_60") or data.get("hv60")

if iv_rank is not None:
    print(f"IV Rank (52-week)      : {iv_rank*100:.1f}%")
    if iv_rank > 0.5:
        print("  -> IV is elevated vs recent history. Options are relatively rich.")
    else:
        print("  -> IV is depressed vs recent history. Options are relatively cheap.")
if iv_pct is not None:
    print(f"IV Percentile          : {iv_pct*100:.1f}%")
if hv_30 is not None:
    print(f"Realized Vol (30d)     : {hv_30*100:.1f}%")
if hv_60 is not None:
    print(f"Realized Vol (60d)     : {hv_60*100:.1f}%")
if atm_iv is not None and hv_30 is not None:
    vrp = atm_iv - hv_30
    print(f"Vol Risk Premium (IV-HV30): {vrp*100:+.1f}%")
    if vrp > 0:
        print("  -> IV > realized vol: market pays a premium for protection.")
    else:
        print("  -> IV < realized vol: market is underpricing near-term risk.")

# --- Term structure ---
# Contango (near < far): normal; carry favors short near-term vol.
# Backwardation (near > far): stress signal; the market fears near-term events.
term_structure = (
    data.get("term_structure")
    or (data.get("volatility") or {}).get("term_structure")
    or []
)
if term_structure:
    print("\n--- Term Structure (IV by Expiration) ---")
    print(f"  {'Expiration':<14} {'DTE':>6} {'IV':>10}")
    print(f"  {'-'*32}")
    for row in term_structure:
        exp = row.get("expiration") or row.get("expiry") or "?"
        dte = row.get("dte")
        iv  = row.get("iv") or row.get("atm_iv")
        d_str = f"{dte:.0f}" if dte is not None else "n/a"
        i_str = f"{iv*100:.2f}%" if iv is not None else "n/a"
        print(f"  {str(exp):<14} {d_str:>6} {i_str:>10}")
    # Detect contango vs backwardation
    ivs = [r.get("iv") or r.get("atm_iv") for r in term_structure if r.get("iv") or r.get("atm_iv")]
    if len(ivs) >= 2:
        if ivs[0] < ivs[-1]:
            print("  Shape: CONTANGO — near-term IV lower than long-term IV (normal)")
        else:
            print("  Shape: BACKWARDATION — near-term IV higher than long-term (stress signal)")

# --- Skew ---
# Skew measures the asymmetry of the vol smile.
# 25-delta risk reversal = IV(25d put) - IV(25d call).
# Negative (put skew): market pays more for downside protection — typical for equities.
# Positive (call skew): market fears upside moves more (common in commodities/crypto).
skew = data.get("skew") or (data.get("volatility") or {}).get("skew") or {}
if skew:
    print("\n--- Volatility Skew ---")
    rr_25  = skew.get("risk_reversal_25d") or skew.get("rr_25")
    fly_25 = skew.get("butterfly_25d")     or skew.get("fly_25")
    slope  = skew.get("slope")             or skew.get("skew_slope")
    if rr_25 is not None:
        print(f"  25-delta risk reversal : {rr_25*100:+.2f}%")
        if rr_25 < 0:
            print("  -> Put skew dominates: market hedging downside.")
        else:
            print("  -> Call skew dominates: market hedging upside.")
    if fly_25 is not None:
        print(f"  25-delta butterfly     : {fly_25*100:.2f}%  (smile curvature)")
    if slope is not None:
        print(f"  Skew slope             : {slope:.4f}")
    for k, v in skew.items():
        if k not in ("risk_reversal_25d","rr_25","butterfly_25d","fly_25","slope","skew_slope"):
            print(f"  {k:<30} {v}")

# --- Vol regime ---
vol_regime = data.get("vol_regime") or (data.get("volatility") or {}).get("regime") or {}
if vol_regime:
    print("\n--- Volatility Regime ---")
    for k, v in vol_regime.items():
        print(f"  {k:<30} {v}")

# --- Forward volatility ---
# Implied forward vol from tenor A to tenor B derived from the term structure.
# Forward vol is used to price calendar spreads and to detect where the market
# is pricing in a specific event (e.g., earnings, FOMC).
forward_vol = (
    data.get("forward_vol")
    or data.get("forward_volatility")
    or (data.get("volatility") or {}).get("forward_vol")
    or []
)
if forward_vol:
    print("\n--- Forward Volatility ---")
    if isinstance(forward_vol, list):
        print(f"  {'From':>8} {'To':>8} {'Fwd IV':>10}")
        print(f"  {'-'*28}")
        for row in forward_vol:
            t1  = row.get("from") or row.get("start_dte")
            t2  = row.get("to")   or row.get("end_dte")
            fiv = row.get("forward_iv") or row.get("iv")
            t1s = str(t1)          if t1  is not None else "n/a"
            t2s = str(t2)          if t2  is not None else "n/a"
            fvs = f"{fiv*100:.2f}%" if fiv is not None else "n/a"
            print(f"  {t1s:>8} {t2s:>8} {fvs:>10}")
    else:
        for k, v in forward_vol.items():
            print(f"  {k:<30} {v}")

# --- Remaining top-level fields ---
printed_keys = {
    "atm_iv", "volatility", "vol", "term_structure", "skew",
    "vol_regime", "forward_vol", "forward_volatility",
    "iv_rank", "iv_percentile", "hv30", "hv60", "summary",
}
remaining = {k: v for k, v in data.items() if k not in printed_keys and v is not None}
if remaining:
    print("\n--- Additional Metrics ---")
    for k, v in remaining.items():
        if not isinstance(v, (dict, list)):
            print(f"  {k:<30} {v}")

print("""
--- When to act on vol data ---
  IV Rank > 70  : selling premium (covered calls, cash-secured puts, strangles)
                  has historically been favorable.
  IV Rank < 30  : buying vol (long calls, puts, or straddles) is relatively cheap.
  Backwardation : near-term event risk priced in. Consider calendar spreads or
                  long near-term straddles funded by selling further-dated options.
  Steep put skew: tail hedging is expensive. Collars and put spreads cost more
                  than historical average.
  High VRP      : the market consistently overprices vol -> structural premium
                  selling edge exists for disciplined traders.
""")
