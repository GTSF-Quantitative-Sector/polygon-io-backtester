from datetime import date

import pytest
from polygon.rest.models.financials import StockFinancial

from backtester import async_polygon
from backtester.config import KEY
from tests.fixtures.aiohttp_fixtures import (
    mock_aiohttp_financials_failed,
    mock_aiohttp_financials_success,
    mock_aiohttp_get_price_past,
    mock_aiohttp_get_price_today,
    mock_aiohttp_get_price_value_error,
    mock_aiohttp_timeout,
)


@pytest.mark.asyncio
async def test_aenter_aexit():
    temp = None
    async with async_polygon.Client(KEY, timeout=10) as client:
        assert client.active
        assert client.timeout == 10
        temp = client

    assert not temp.active


@pytest.mark.asyncio
async def test_get_financials_timeout(mock_aiohttp_timeout):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_timeout

        with pytest.raises(TimeoutError):
            await client.get_financials("AAPL")


@pytest.mark.asyncio
async def test_get_financials_success(mock_aiohttp_financials_success):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_financials_success
        current, last = await client.get_financials("AAPL")

        # assert right objects are being returned
        assert isinstance(current, StockFinancial)
        assert isinstance(last, StockFinancial)

        # sampling of sanity check attributes
        assert current.company_name == last.company_name
        assert current.company_name == "Apple Inc."
        assert current.end_date is not None and last.end_date is not None
        assert current.end_date > last.end_date


@pytest.mark.asyncio
async def test_get_financials_failed(mock_aiohttp_financials_failed):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_financials_failed

        with pytest.raises(ValueError):
            await client.get_financials("AAPL")


@pytest.mark.asyncio
async def test_get_price_today(mock_aiohttp_get_price_today):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_get_price_today

        # ensure leaving query_date as none and setting it as today have same function
        price_1 = await client.get_price("AAPL")
        price_2 = await client.get_price("AAPL", query_date=date.today())

        assert price_1 == price_2
        assert price_1 == 141.86
        assert isinstance(price_1, float)
        assert isinstance(price_1, float)


@pytest.mark.asyncio
async def test_get_price_timeouts(mock_aiohttp_timeout):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_timeout

        with pytest.raises(TimeoutError):
            await client.get_price("AAPL")
        with pytest.raises(TimeoutError):
            await client.get_price("AAPL", query_date=date(2020, 1, 9))


@pytest.mark.asyncio
async def test_get_price_past(mock_aiohttp_get_price_past):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_get_price_past

        price = await client.get_price("AAPL", query_date=date(2022, 11, 4))
        assert isinstance(price, float)
        assert price == 138.38


@pytest.mark.asyncio
async def test_get_price_value_error(mock_aiohttp_get_price_value_error):
    async with async_polygon.Client(KEY) as client:
        assert client.session is not None
        await client.session.close()
        client.session = mock_aiohttp_get_price_value_error

        with pytest.raises(ValueError):
            await client.get_price("AAPL", query_date=date(2022, 11, 4))
