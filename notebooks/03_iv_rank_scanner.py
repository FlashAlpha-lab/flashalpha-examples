# # IV Rank Scanner Across Tickers
#
# Scan a universe of tickers and rank them by ATM implied volatility.
# Useful for finding rich premium-selling candidates.
# Requires: pip install flashalpha

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

TICKERS = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "AMZN", "META", "MSFT"]

# --- Collect vol data for each ticker ---
rows = []
for ticker in TICKERS:
    try:
        summary = fa.stock_summary(ticker)
        vol     = summary.get("volatility") or {}
        price   = summary.get("price") or {}

        atm_iv   = vol.get("atm_iv") or vol.get("iv30") or vol.get("current_iv")
        iv_rank  = vol.get("iv_rank") or vol.get("ivr")
        iv_pct   = vol.get("iv_percentile") or vol.get("ivp")
        spot     = price.get("last") or price.get("close")

        rows.append({
            "ticker":     ticker,
            "spot":       spot,
            "atm_iv":     atm_iv,
            "iv_rank":    iv_rank,
            "iv_pct":     iv_pct,
        })
    except Exception as exc:
        print(f"  {ticker}: error — {exc}")

# --- Sort by ATM IV descending (richest premium first) ---
rows.sort(key=lambda r: r["atm_iv"] or 0, reverse=True)

# --- Print table ---
header = f"{'Ticker':<8} {'Spot':>8} {'ATM IV':>10} {'IV Rank':>10} {'IV Pct':>10}"
print(header)
print("-" * len(header))
for r in rows:
    iv_str   = f"{r['atm_iv']*100:.1f}%"  if r["atm_iv"]  is not None else "n/a"
    ivr_str  = f"{r['iv_rank']*100:.1f}%"  if r["iv_rank"] is not None else "n/a"
    ivp_str  = f"{r['iv_pct']*100:.1f}%"   if r["iv_pct"]  is not None else "n/a"
    spot_str = f"${r['spot']:.2f}"          if r["spot"]    is not None else "n/a"
    print(f"{r['ticker']:<8} {spot_str:>8} {iv_str:>10} {ivr_str:>10} {ivp_str:>10}")

print("\nHighest ATM IV = richest premium. IV Rank > 50 suggests elevated vol.")
