# # Build a GEX Dashboard
#
# Visualize Gamma Exposure (GEX) by strike for SPY.
# Gamma flip, call wall, and put wall are annotated directly on the chart.
# Requires: pip install flashalpha matplotlib

import os
import matplotlib
matplotlib.use("Agg")  # headless-safe; remove if running interactively
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# --- Fetch data ---
gex_data = fa.gex("SPY")
levels   = fa.exposure_levels("SPY")

strikes = [s["strike"] for s in gex_data["strikes"]]
gex_vals = [s["gex"] for s in gex_data["strikes"]]
lvl = levels["levels"]

# --- Regime interpretation ---
net_gex = sum(gex_vals)
regime  = "Positive GEX — dealers are long gamma (dampening moves)" if net_gex > 0 \
          else "Negative GEX — dealers are short gamma (amplifying moves)"
print(f"Net GEX: {net_gex:,.0f}  |  Regime: {regime}")

# --- Top 5 strikes by absolute GEX ---
top5 = sorted(zip(strikes, gex_vals), key=lambda x: abs(x[1]), reverse=True)[:5]
print("\nTop 5 strikes by |GEX|:")
for strike, g in top5:
    print(f"  {strike:>7.1f}  GEX={g:>15,.0f}")

# --- Plot ---
colors = ["#2ecc71" if g >= 0 else "#e74c3c" for g in gex_vals]

fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(strikes, gex_vals, width=1.0, color=colors, alpha=0.85)

for label, key, color in [
    ("Gamma Flip", "gamma_flip", "#f39c12"),
    ("Call Wall",  "call_wall",  "#2980b9"),
    ("Put Wall",   "put_wall",   "#8e44ad"),
]:
    val = lvl.get(key)
    if val:
        ax.axvline(val, color=color, linewidth=1.8, linestyle="--", label=f"{label}: {val}")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e9:.1f}B"))
ax.set_xlabel("Strike")
ax.set_ylabel("GEX ($ billions)")
ax.set_title("SPY Gamma Exposure by Strike")
ax.legend()
ax.axhline(0, color="white", linewidth=0.6, alpha=0.4)
fig.tight_layout()
fig.savefig("spy_gex_dashboard.png", dpi=150)
print("\nChart saved to spy_gex_dashboard.png")
