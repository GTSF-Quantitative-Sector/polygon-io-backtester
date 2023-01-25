from datetime import date
import pytest
from asyncmock import AsyncMock

from backtester.ticker_date import Ticker, TickerDate
from backtester.async_polygon import AsyncPolygon
from backtester.config import KEY

from polygon.rest.models.financials import StockFinancial

SAMPLE_STOCK_PRICE = 1885.0

@pytest.fixture
def example_last_financials():
    return StockFinancial.from_dict({
        "company_name": "AAPL",
        "fiscal_year": "2020",
        "financials": {
            "cash_flow_statement": {
                "net_cash_flow": {
                    "value": 10.0
                }
            }
        }
    })

@pytest.fixture
def example_current_financials():
    return StockFinancial.from_dict({
        "company_name": "AAPL",
        "fiscal_year": "2021",
        "financials": {
            "cash_flow_statement": {
                "net_cash_flow": {
                    "value": 15.0
                }
            }
        }
    })

@pytest.fixture
def mock_async_polygon(example_last_financials, example_current_financials):
    mock = AsyncMock()
    aenter_mock = AsyncMock()
    aenter_mock.get_financials = AsyncMock(return_value=(example_current_financials, example_last_financials))
    aenter_mock.get_price = AsyncMock(return_value=SAMPLE_STOCK_PRICE)
    mock.aenter_return_value = aenter_mock
    return mock

def test_ticker_initialization():
    t = Ticker("AAPL", "Technology")

    assert t.name == "AAPL"
    assert t.sector == "Technology"

@pytest.mark.asyncio
async def test_ticker_date_initialization():
    async with AsyncPolygon(KEY) as client:
        t = Ticker("AAPL", "Technology")
        td = TickerDate(t, date.today(), client)

        assert not td.synced
        assert td.query_date == date.today()

        with pytest.raises(AttributeError):
            td.current_financials

        with pytest.raises(AttributeError):
            td.last_financials

        with pytest.raises(AttributeError):
            td.price

@pytest.mark.asyncio
async def test_ticker_date_sync(mock_async_polygon):
    async with mock_async_polygon as client:
        t = Ticker("AAPL", "Technology")
        td = TickerDate(t, date.today(), client)
        await td.sync()

        assert td.price == SAMPLE_STOCK_PRICE
        assert td.synced
        
        # small selection of fields present on the StockFinancial object
        assert td.last_financials.fiscal_year == "2020"
        assert td.last_financials.financials.cash_flow_statement.net_cash_flow.value == 10.0

        assert td.current_financials.fiscal_year == "2021"
        assert td.current_financials.financials.cash_flow_statement.net_cash_flow.value == 15.0