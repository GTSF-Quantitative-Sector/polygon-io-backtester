import pytest

from backtester import Algorithm, StockFinancial
from tests.fixtures.ticker_date_fixtures import sample_ticker_dates


@pytest.mark.asyncio
async def test_group_by_sort(sample_ticker_dates):
    algo = Algorithm([])

    ticker_scores = []
    count = 0
    for td in sample_ticker_dates:
        ticker_scores.append((td, count))
        count += 1

    # 4 different sectors in sample_ticker_dates
    tickers = algo._group_by_sort(ticker_scores)
    assert len(tickers) == 4

    assert tickers[0].name == "MS"
    assert tickers[0].sector == "Financials"

    assert tickers[1].name == "TMO"
    assert tickers[1].sector == "Healthcare"

    assert tickers[2].name == "DE"
    assert tickers[2].sector == "Industrials"

    assert tickers[3].name == "ADBE"
    assert tickers[3].sector == "Technology"


@pytest.mark.asyncio
async def test_rank_tickers(sample_ticker_dates):
    class TestAlgorithm(Algorithm):

        # simply score by price
        async def score(
            self,
            current_financials: StockFinancial,
            last_financials: StockFinancial,
            current_price: float,
        ) -> float:
            return current_price

    algo = TestAlgorithm([])

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
