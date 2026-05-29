# ---
# slug: 01-gex-dashboard
# title: Build a GEX Dashboard in 30 Lines
# tier: free
# runtime_budget_seconds: 60
# max_api_calls: 4
# endpoints_used:
#   - /v1/exposure/gex/{symbol}
#   - /v1/exposure/levels/{symbol}
# tier_gated_cells: []
# sdk_version_min: "1.0.1"
# utm_campaign: 01-gex-dashboard
# expected_artifacts:
#   dataframes: []
#   charts: [gex_chart.png]
# last_validated_live: 2026-05-27
# ---

# %% [markdown]
# # Build a GEX Dashboard in 30 Lines
#
# > 🔑 Get a free FlashAlpha API key (5 req/day, no card):
# >   https://flashalpha.com/profile?utm_source=github-cookbook&utm_medium=notebook&utm_campaign=01-gex-dashboard
# >
# > Tier required: **Free** · [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FlashAlpha-lab/flashalpha-examples/blob/main/notebooks/tier-a-hooks/01-gex-dashboard.ipynb)

# %% [markdown]
# Visualize Gamma Exposure (GEX) by strike for SPY. Gamma flip, call wall, and
# put wall are annotated directly on the chart.

# %%
import os

import matplotlib
matplotlib.use("Agg")  # headless-safe; remove if running interactively
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# %%
# Fetch GEX strikes and key levels — these are the two Free-tier calls.
gex_data = fa.gex("SPY")           # /v1/exposure/gex/SPY
levels = fa.exposure_levels("SPY")  # /v1/exposure/levels/SPY

strikes = [s["strike"] for s in gex_data["strikes"]]
gex_vals = [s["net_gex"] for s in gex_data["strikes"]]
lvl = levels["levels"]

net_gex = sum(gex_vals)
regime = (
    "Positive GEX — dealers are long gamma (dampening moves)"
    if net_gex > 0
    else "Negative GEX — dealers are short gamma (amplifying moves)"
)
print(f"Net GEX: {net_gex:,.0f}  |  Regime: {regime}")

# %%
top5 = sorted(zip(strikes, gex_vals), key=lambda x: abs(x[1]), reverse=True)[:5]
print("Top 5 strikes by |GEX|:")
for strike, g in top5:
    print(f"  {strike:>7.1f}  GEX={g:>15,.0f}")

# %%
colors = ["#2ecc71" if g >= 0 else "#e74c3c" for g in gex_vals]

fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(strikes, gex_vals, width=1.0, color=colors, alpha=0.85)

for label, key, color in [
    ("Gamma Flip", "gamma_flip", "#f39c12"),
    ("Call Wall", "call_wall", "#2980b9"),
    ("Put Wall", "put_wall", "#8e44ad"),
]:
    val = lvl.get(key)
    if val:
        ax.axvline(val, color=color, linewidth=1.8, linestyle="--", label=f"{label}: {val}")

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e9:.1f}B"))
ax.set_xlabel("Strike")
ax.set_ylabel("GEX ($ billions)")
ax.set_title("SPY Gamma Exposure by Strike")
ax.legend()
ax.axhline(0, color="#888888", linewidth=0.6, alpha=0.4)
fig.tight_layout()
fig.savefig("gex_chart.png", dpi=150)
print("Chart saved to gex_chart.png")

# %% [markdown]
# ## What to try next
#
# - 🔁 Backtest this with historical replay (Alpha) → https://flashalpha.com/pricing?utm_source=github-cookbook&utm_campaign=01-gex-dashboard
# - 💬 Discord: https://flashalpha.com/discord
# - 📚 More recipes: https://github.com/FlashAlpha-lab/flashalpha-examples
# - 🤖 Use with Claude/Cursor via MCP: https://flashalpha.com/docs/mcp
