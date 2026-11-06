# # sell-window: Should You Sell Options Today?
#
# Option sellers get wiped out on a few bad days. sell-window tells you which
# days to stay out, and on the days it says sell, it hands you the trades:
# which expiry, which strikes and how to exit. Every session, for SPY, QQQ and
# IWM. More than 5 million backtests led to this one endpoint.
#
#   fa.sell_window(symbol)  -> /v1/strategies/sell-window/{symbol}
#
# Each of the four windows (the same-day expiry, then the expiries closest to
# one week, two weeks and one month out) says sell, skip or unavailable. On a
# skip there is nothing to do. Treat unavailable like a skip.
#
# Plans: Basic+ through November 2026, Growth+ from December 1, 2026.
# Docs: https://flashalpha.com/docs/lab-api-strategies-sell-window
# Backtest: https://flashalpha.com/articles/sell-window-backtest-every-trade-2018-2026
#
# Past results do not guarantee future returns, and short options can lose more
# than the premium collected. This is data, not investment advice.
#
# Requires: pip install "flashalpha>=1.4.0"

import os
from flashalpha import FlashAlpha

fa = FlashAlpha(os.environ["FLASHALPHA_API_KEY"])

for symbol in ("SPY", "QQQ", "IWM"):
    answer = fa.sell_window(symbol)
    print(f"{symbol} session {answer['session']}")
    if answer.get("legs_indicative"):
        print("  Quotes are from before the 09:35 ET entry. Call again at or after 09:35 ET.")
    for window in answer["windows"]:
        print(f"  {window.get('expiry', 'no listed expiry')}: {window['action']}")
        for trade in window.get("candidates", []):
            credit = trade.get("mid_credit")
            credit_text = f"${credit * 100:,.2f} credit at mid" if credit is not None else "no quote"
            print(f"    {trade['structure']}, {credit_text}, exit: {trade['exit']}")
