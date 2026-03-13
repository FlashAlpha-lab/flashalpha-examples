"""
Integration tests for the FlashAlpha API examples.

Requires a live API key in the FLASHALPHA_API_KEY environment variable.
All tests are marked with @pytest.mark.integration and are skipped when the
key is absent so CI stays green without credentials.

Run with:
    pytest tests/test_examples.py -m integration -v
"""

import os
import pytest

pytestmark = pytest.mark.integration

API_KEY = os.environ.get("FLASHALPHA_API_KEY")

if not API_KEY:
    pytest.skip(
        "FLASHALPHA_API_KEY not set — skipping integration tests",
        allow_module_level=True,
    )

from flashalpha import FlashAlpha  # noqa: E402 — import after skip guard

fa = FlashAlpha(API_KEY)
SYMBOL = "SPY"


# ---------------------------------------------------------------------------
# GEX
# ---------------------------------------------------------------------------
def test_gex_returns_strikes_list():
    result = fa.gex(SYMBOL)
    assert "strikes" in result, f"Expected 'strikes' key, got: {list(result.keys())}"
    strikes = result["strikes"]
    assert isinstance(strikes, list)
    assert len(strikes) > 0
    first = strikes[0]
    assert "strike" in first, f"Strike entry missing 'strike' key: {first}"
    assert "gex" in first,    f"Strike entry missing 'gex' key: {first}"


def test_gex_with_filters():
    """fa.gex() accepts optional expiration and min_oi filters without error."""
    result = fa.gex(SYMBOL, min_oi=100)
    assert "strikes" in result


# ---------------------------------------------------------------------------
# Exposure levels
# ---------------------------------------------------------------------------
def test_exposure_levels_returns_levels_dict():
    result = fa.exposure_levels(SYMBOL)
    assert "levels" in result, f"Expected 'levels' key, got: {list(result.keys())}"
    lvl = result["levels"]
    assert isinstance(lvl, dict)
    for key in ("gamma_flip", "call_wall", "put_wall"):
        assert key in lvl, f"Missing level key: {key}"


# ---------------------------------------------------------------------------
# Stock quote
# ---------------------------------------------------------------------------
def test_stock_quote_returns_bid_ask_mid():
    result = fa.stock_quote(SYMBOL)
    for field in ("bid", "ask", "mid"):
        assert field in result, f"stock_quote missing field: {field}"
    assert result["ask"] >= result["bid"] >= 0


# ---------------------------------------------------------------------------
# BSM greeks
# ---------------------------------------------------------------------------
def test_greeks_returns_first_order_with_delta():
    result = fa.greeks(spot=580, strike=585, dte=7, sigma=0.18, type="call")
    assert "first_order" in result, f"Expected 'first_order', got: {list(result.keys())}"
    fo = result["first_order"]
    assert "delta" in fo, f"'first_order' missing 'delta': {fo}"
    assert 0.0 <= fo["delta"] <= 1.0, f"Call delta out of range: {fo['delta']}"


# ---------------------------------------------------------------------------
# IV solver
# ---------------------------------------------------------------------------
def test_iv_solver_returns_implied_volatility():
    result = fa.iv(spot=580, strike=585, dte=7, price=4.50, type="call")
    assert "implied_volatility" in result, f"Expected 'implied_volatility', got: {list(result.keys())}"
    iv = result["implied_volatility"]
    assert isinstance(iv, float)
    assert 0.0 < iv < 5.0, f"IV looks unreasonable: {iv}"


# ---------------------------------------------------------------------------
# Kelly sizing
# ---------------------------------------------------------------------------
def test_kelly_returns_sizing_dict():
    result = fa.kelly(
        spot=580, strike=585, dte=7, sigma=0.18, premium=4.50, mu=0.001, type="call"
    )
    # Accept any of the common key names the API might use
    sizing_keys = {"kelly_fraction", "fraction", "f"}
    found = sizing_keys & set(result.keys())
    assert found, f"Kelly response missing expected sizing key. Got keys: {list(result.keys())}"


# ---------------------------------------------------------------------------
# Vol surface
# ---------------------------------------------------------------------------
def test_surface_returns_data():
    result = fa.surface(SYMBOL)
    assert "surface" in result, f"Expected 'surface' key, got: {list(result.keys())}"
    surface = result["surface"]
    assert isinstance(surface, list)
    assert len(surface) > 0
    first = surface[0]
    for field in ("strike", "dte", "iv"):
        assert field in first, f"Surface entry missing '{field}': {first}"


# ---------------------------------------------------------------------------
# DEX / VEX / CHEX (smoke tests)
# ---------------------------------------------------------------------------
def test_dex_returns_data():
    result = fa.dex(SYMBOL)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_vex_returns_data():
    result = fa.vex(SYMBOL)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_chex_returns_data():
    result = fa.chex(SYMBOL)
    assert isinstance(result, dict)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Account info
# ---------------------------------------------------------------------------
def test_account_returns_info():
    result = fa.account()
    assert isinstance(result, dict)
    assert len(result) > 0
