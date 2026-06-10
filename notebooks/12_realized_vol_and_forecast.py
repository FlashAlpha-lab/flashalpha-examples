# # Realized Volatility and Conditional Vol Forecasts
#
# Two Alpha+ endpoints that quantify a ticker's volatility from the price
# series itself, with no reference to the options market:
#
#   fa.realized_volatility(symbol)  -> /v1/volatility/realized/{symbol}
#     Range-based realized (historical) vol estimators computed over fixed
#     10/20/30-day windows. Five estimators are returned, each annualized
#     and expressed in percent (nullable when the window is too short):
#       close_to_close  - the classic estimator (close-to-close log returns)
#       parkinson       - uses the high-low range (more efficient)
#       garman_klass    - uses open/high/low/close (more efficient still)
#       rogers_satchell - drift-independent; valid with a trending price
#       yang_zhang      - combines overnight + intraday; handles gaps best
#
#   fa.volatility_forecast(symbol, dist=...) -> /v1/volatility/forecast/{symbol}
#     Conditional one-step and multi-step vol forecasts via three models:
#       ewma   - exponentially weighted moving average (RiskMetrics, lambda=0.94)
#       har_rv - Heterogeneous AutoRegressive RV (daily/weekly/monthly terms)
#       garch  - GARCH(1,1) fit by MLE; pass dist="student_t" (default) or
#                "gaussian" to set the error distribution.
#
# Use realized vol as the "what actually happened" baseline, and the forecast
# block as the "what comes next" view. Comparing either against implied vol
# (fa.volatility / fa.vrp) tells you whether options are rich or cheap.
#
# Requires: pip install flashalpha  (Alpha+ tier API key)

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

SYMBOL = "SPY"


def fmt_pct(v):
    return f"{v:.2f}%" if v is not None else "n/a"


# --- Realized volatility ---
rv = fa.realized_volatility(SYMBOL)

print(f"=== Realized Volatility: {SYMBOL} ===")
print(f"As of            : {rv.get('as_of', 'n/a')}")
und = rv.get("underlying_price")
if und is not None:
    print(f"Underlying price : {und:,.2f}")

estimators = rv.get("estimators") or {}
if estimators:
    print("\n--- Annualized realized vol by estimator (percent) ---")
    print(f"  {'Estimator':<18} {'rv10':>8} {'rv20':>8} {'rv30':>8}")
    print(f"  {'-'*44}")
    for name in (
        "close_to_close",
        "parkinson",
        "garman_klass",
        "rogers_satchell",
        "yang_zhang",
    ):
        block = estimators.get(name) or {}
        print(
            f"  {name:<18}"
            f" {fmt_pct(block.get('rv10')):>8}"
            f" {fmt_pct(block.get('rv20')):>8}"
            f" {fmt_pct(block.get('rv30')):>8}"
        )

# --- Conditional vol forecast ---
# dist controls the GARCH error distribution: student_t (default) captures
# fatter tails than gaussian and is usually the better fit for equity returns.
fc = fa.volatility_forecast(SYMBOL, dist="student_t")

print(f"\n=== Volatility Forecast: {SYMBOL} ===")
print(f"As of : {fc.get('as_of', 'n/a')}")

# EWMA
ewma = fc.get("ewma") or {}
if ewma:
    lam = ewma.get("lambda")
    print("\n--- EWMA (RiskMetrics) ---")
    if lam is not None:
        print(f"  lambda            : {lam}")
    print(f"  Vol (annualized)  : {fmt_pct(ewma.get('vol_annualized'))}")
    print(f"  Next-day forecast : {fmt_pct(ewma.get('next_day_forecast'))}")

# HAR-RV
har = fc.get("har_rv") or {}
if har:
    print("\n--- HAR-RV ---")
    print(f"  Vol (annualized)  : {fmt_pct(har.get('vol_annualized'))}")
    comp = har.get("components") or {}
    if comp:
        print(
            f"  Components        : "
            f"daily={fmt_pct(comp.get('daily'))}  "
            f"weekly={fmt_pct(comp.get('weekly'))}  "
            f"monthly={fmt_pct(comp.get('monthly'))}"
        )
    print(f"  Next-day forecast : {fmt_pct(har.get('next_day_forecast'))}")

# GARCH(1,1)
garch = fc.get("garch") or {}
if garch:
    print("\n--- GARCH(1,1) MLE ---")
    print(f"  Model         : {garch.get('model', 'n/a')}")
    print(f"  Distribution  : {garch.get('distribution', 'n/a')}")
    print(f"  Converged     : {garch.get('converged')}")

    params = garch.get("params") or {}
    if params:
        # omega + alpha + beta define the conditional variance recursion;
        # dof is present only for the student_t distribution.
        parts = []
        for k in ("omega", "alpha", "beta", "dof"):
            v = params.get(k)
            if v is not None:
                parts.append(f"{k}={v:.4g}")
        if parts:
            print(f"  Params        : {', '.join(parts)}")

    pers = garch.get("persistence")
    if pers is not None:
        # persistence = alpha + beta. Close to 1 -> shocks decay slowly and
        # vol is highly persistent; >= 1 leaves long-run vol undefined.
        print(f"  Persistence   : {pers:.4f}")
    print(f"  Long-run vol  : {fmt_pct(garch.get('long_run_vol_annualized'))}")
    hl = garch.get("half_life_days")
    if hl is not None:
        print(f"  Half-life     : {hl:.1f} days")

    forecast = garch.get("forecast") or []
    if forecast:
        print("\n  Multi-step forecast (annualized vol):")
        print(f"    {'Horizon (days)':>14} {'Vol':>10}")
        print(f"    {'-'*26}")
        for pt in forecast:
            h = pt.get("horizon_days")
            h_str = f"{h}" if h is not None else "n/a"
            print(f"    {h_str:>14} {fmt_pct(pt.get('vol_annualized')):>10}")

print(
    """
--- How to use these together ---
  realized vol  : the ground truth of how much the underlying actually moved.
                  Yang-Zhang is the most efficient single estimator; compare
                  rv10 vs rv30 to see whether vol is rising or mean-reverting.
  ewma / har_rv : fast, model-light next-day vol nowcasts. HAR-RV's daily,
                  weekly, and monthly terms capture vol clustering across
                  horizons better than a single decay factor.
  garch         : a fitted conditional-vol model with a term structure of
                  forecasts. Persistence near 1 means vol shocks fade slowly;
                  long-run vol is the level the forecast curve reverts toward.
  vs implied    : if forecast/realized vol sits well below implied (fa.vrp),
                  options are rich and premium selling is favored, and the
                  reverse when forecasts run hot.
"""
)
