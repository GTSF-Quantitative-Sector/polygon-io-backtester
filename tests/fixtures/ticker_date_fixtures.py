import pytest
from backtester.ticker_date import Ticker, TickerDate
from backtester import StockFinancial


@pytest.fixture
def sample_ticker_dates():
    tds = [
        TickerDate(Ticker("AAPL", "Technology"), None, None),
        TickerDate(Ticker("META", "Technology"), None, None),
        TickerDate(Ticker("ADBE", "Technology"), None, None),
        TickerDate(Ticker("RTX", "Industrials"), None, None),
        TickerDate(Ticker("APD", "Industrials"), None, None),
        TickerDate(Ticker("URI", "Industrials"), None, None),
        TickerDate(Ticker("DE", "Industrials"), None, None),
        TickerDate(Ticker("MDT", "Healthcare"), None, None),
        TickerDate(Ticker("VRTX", "Healthcare"), None, None),
        TickerDate(Ticker("TMO", "Healthcare"), None, None),
        TickerDate(Ticker("ICE", "Financials"), None, None),
        TickerDate(Ticker("MS", "Financials"), None, None),
    ]

    prices = [1, 2, 3, 5, 3, 2, 1, 2, 2.5, 1.5, 4, 2]

    for td, price in zip(tds, prices):
        td._price = price
        td._current_financials = StockFinancial()
        td._last_financials = StockFinancial()
        td.synced = True

    return tds
