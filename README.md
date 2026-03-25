# FlashAlpha Examples

Practical Python examples for options analytics, gamma exposure, volatility surface
modeling, dealer positioning, 0DTE analytics, and more — all powered by the
[FlashAlpha API](https://flashalpha.com).

Each file in `notebooks/` is a self-contained Python script. Run it directly,
paste it into a Jupyter notebook, or share it as-is.

Keywords: gamma exposure python, options analytics API, 0DTE options analytics,
volatility surface python, implied volatility rank, dealer positioning, GEX dashboard,
SVI volatility model, variance swap, options flow python, options greeks API,
IV rank scanner, volatility skew python, options regime analysis.

---

## Examples

| File | Title | What it shows |
|------|-------|---------------|
| `notebooks/01_quick_start.py` | Getting Started with FlashAlpha | GEX, exposure levels, live quote, BSM greeks in 30 lines |
| `notebooks/02_gex_dashboard.py` | Build a GEX Dashboard | Bar chart of gamma exposure by strike with gamma flip, call wall, put wall annotated |
| `notebooks/03_iv_rank_scanner.py` | IV Rank Scanner | Scan SPY/QQQ/AAPL/TSLA/NVDA/AMZN/META/MSFT and rank by ATM implied volatility |
| `notebooks/04_vol_surface_3d.py` | 3D Volatility Surface | 3D scatter/mesh of the SPY implied volatility surface (strike x DTE x IV) |
| `notebooks/05_dealer_positioning.py` | Understanding Dealer Positioning | Net GEX/DEX/VEX/CHEX, hedging estimates, zero-DTE contribution, narrative |
| `notebooks/06_kelly_sizing.py` | Kelly Criterion for Options | Optimal position sizing via greeks, IV solver, and Kelly fraction |
| `notebooks/07_zero_dte_analytics.py` | 0DTE Intraday Analytics | Regime, expected move, pin risk, dealer hedging flows, theta decay for same-day expiries |
| `notebooks/08_advanced_volatility.py` | Advanced Volatility: SVI and Variance Surface | SVI parameters, variance surface, calendar/butterfly arbitrage detection, greeks surfaces, variance swap rates |
| `notebooks/09_volatility_analysis.py` | Comprehensive Volatility Analysis | IV rank, term structure, skew, vol risk premium, forward vol, vol regime for TSLA |

---

## Installation

```bash
pip install flashalpha matplotlib numpy
```

Set your API key once:

```bash
export FLASHALPHA_API_KEY="your_key_here"
```

Then run any example:

```bash
python notebooks/01_quick_start.py
```

Get an API key at [flashalpha.com](https://flashalpha.com).

---

## Running the Tests

```bash
pip install pytest

# Syntax validation (no API key needed)
pytest tests/test_notebooks_syntax.py -v

# Integration tests (requires FLASHALPHA_API_KEY)
pytest tests/test_examples.py -m integration -v
```

---

## API Methods Used

| Method | Description | Tier |
|--------|-------------|------|
| `fa.gex(symbol)` | Gamma exposure by strike | Public |
| `fa.dex(symbol)` | Delta exposure | Public |
| `fa.vex(symbol)` | Vanna exposure | Public |
| `fa.chex(symbol)` | Charm exposure | Public |
| `fa.exposure_levels(symbol)` | Key levels (gamma flip, call/put wall) | Public |
| `fa.exposure_summary(symbol)` | Full exposure summary | Growth+ |
| `fa.narrative(symbol)` | Verbal regime analysis | Growth+ |
| `fa.zero_dte(symbol)` | 0DTE regime, expected move, pin risk, hedging, theta decay | Growth+ |
| `fa.stock_quote(ticker)` | Live bid/ask/mid | Public |
| `fa.stock_summary(symbol)` | Price, vol, exposure, macro | Public |
| `fa.greeks(...)` | BSM greeks (delta, gamma, theta, vega) | Public |
| `fa.iv(...)` | Implied vol solver | Public |
| `fa.kelly(...)` | Kelly optimal position sizing | Growth+ |
| `fa.surface(symbol)` | Full IV surface | Public |
| `fa.volatility(symbol)` | IV rank, term structure, skew, vol regime, forward vol | Growth+ |
| `fa.adv_volatility(symbol)` | SVI parameters, variance surface, arbitrage flags, greeks surfaces, variance swap | Alpha+ |
| `fa.options(ticker)` | Options chain metadata | Public |
| `fa.tickers()` | All available tickers | Public |
| `fa.account()` | Account info | Public |

---

## License

MIT. See [LICENSE](LICENSE).
