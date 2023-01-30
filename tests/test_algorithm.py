import pytest

from backtester import Algorithm, StockFinancial
from tests.fixtures.ticker_date_fixtures import sample_ticker_dates

@pytest.mark.asyncio
async def test_rank_tickers(sample_ticker_dates):
    class TestAlgorithm(Algorithm):

        # simply score by price
        async def score(self, current_financials: StockFinancial, last_financials: StockFinancial, current_price: float) -> float:
            return current_price

    algo = TestAlgorithm(None)

    # ensure it is returning num_stocks
    tickers = await algo._rank_tickers(sample_ticker_dates, num_stocks=4)
    assert len(tickers) == 4

    tickers = await algo._rank_tickers(sample_ticker_dates, num_stocks=3)
    assert len(tickers) == 3

    assert tickers[0].name == "RTX"
    assert tickers[0].sector == "Industrials"

    assert tickers[1].name == "ICE"
    assert tickers[1].sector == "Financials"

    assert tickers[2].name == "ADBE"
    assert tickers[2].sector == "Technology"