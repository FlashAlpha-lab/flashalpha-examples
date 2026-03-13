# # 3D Volatility Surface
#
# Fetch the implied volatility surface for SPY and render it as a 3D mesh.
# Strike on X, days-to-expiration on Y, IV on Z.
# Requires: pip install flashalpha matplotlib numpy

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless-safe; remove if running interactively
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — required side-effect import

from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

# --- Fetch surface data ---
surface_resp = fa.surface("SPY")
surface      = surface_resp["surface"]  # list of {strike, expiration, iv, dte, ...}

# --- Build arrays ---
strikes = np.array([p["strike"] for p in surface], dtype=float)
dtes    = np.array([p["dte"]    for p in surface], dtype=float)
ivs     = np.array([p["iv"]     for p in surface], dtype=float)

# --- Scatter-based surface plot ---
fig = plt.figure(figsize=(13, 8))
ax  = fig.add_subplot(111, projection="3d")

sc = ax.scatter(strikes, dtes, ivs * 100,
                c=ivs * 100, cmap="plasma",
                s=18, alpha=0.85, depthshade=True)

fig.colorbar(sc, ax=ax, pad=0.1, label="IV (%)")
ax.set_xlabel("Strike", labelpad=10)
ax.set_ylabel("DTE (days)",  labelpad=10)
ax.set_zlabel("Implied Vol (%)", labelpad=10)
ax.set_title("SPY Implied Volatility Surface", pad=15)
ax.view_init(elev=25, azim=-50)

fig.tight_layout()
fig.savefig("spy_vol_surface_3d.png", dpi=150)
print("3D surface saved to spy_vol_surface_3d.png")

# --- Quick stats ---
print(f"\nStrikes covered : {strikes.min():.0f} – {strikes.max():.0f}")
print(f"DTE range       : {dtes.min():.0f} – {dtes.max():.0f} days")
print(f"IV range        : {ivs.min()*100:.1f}% – {ivs.max()*100:.1f}%")
print(f"ATM 30-DTE IV   : ~{ivs[np.argmin(np.abs(dtes-30))]*100:.1f}%")
