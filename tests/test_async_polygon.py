import pytest

from backtester.config import KEY
from backtester.async_polygon import AsyncPolygon
from tests.fixtures.aiohttp_fixtures import mock_aiohttp_financials_success, mock_aiohttp_financials_timeout
from polygon.rest.models.financials import StockFinancial

@pytest.mark.asyncio
async def test_aenter_aexit():
    temp = None
    async with AsyncPolygon(KEY, timeout=10) as client:
        assert client.active
        assert client.timeout == 10
        temp = client

    assert not temp.active

@pytest.mark.asyncio
async def test_get_financials_success(mock_aiohttp_financials_success):
    async with AsyncPolygon(KEY) as client:
        await client.session.close()
        client.session = mock_aiohttp_financials_success
        current, last = await client.get_financials("AAPL")

        # assert right objects are being returned
        assert isinstance(current, StockFinancial)
        assert isinstance(last, StockFinancial)

        # sampling of sanity check attributes
        assert current.company_name == last.company_name
        assert current.company_name == "Apple Inc."
        assert current.end_date > last.end_date

@pytest.mark.asyncio
async def test_get_financials_timeout(mock_aiohttp_financials_timeout):
    async with AsyncPolygon(KEY) as client:
        await client.session.close()
        client.session = mock_aiohttp_financials_timeout

        with pytest.raises(TimeoutError):
            await client.get_financials("AAPL")
