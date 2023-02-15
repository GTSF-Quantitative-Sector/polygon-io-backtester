import asyncio
from datetime import date, timedelta
from typing import Any, Optional, Tuple

import aiohttp

from backtester.models import StockFinancial, Ticker, TickerDate


class Client:
    """
    Class for interacting with the Polygon.io REST API in an asynchronous fashion
    """

    session: Optional[aiohttp.ClientSession]

    def __init__(self, api_key: str, timeout: Optional[float] = 10):
        """
        Args:
            api_key (str): the Polygon.io API key to use
            timeout (float, optional): default timeout for http requests, defaults to 10 seconds
        """
        self.api_key = api_key
        self.session = None
        self.timeout = timeout
        self.active = False

    async def get_ticker_date(self, ticker: Ticker, query_date: date) -> TickerDate:
        """Get ticker date for specified ticker and query_date

        Args:
            ticker (Ticker): ticker that is being queried
            query_date (date): date that is being queried
        Returns:
            TickerDate: Ticker and associated data for a given date
        """
        financials, price = await asyncio.gather(
            self.get_financials(ticker.name, query_date),
            self.get_price(ticker.name, query_date),
        )
        current_financials, last_financials = financials
        return TickerDate(
            ticker, query_date, current_financials, last_financials, price
        )

    async def get_financials(
        self, ticker: str, query_date: Optional[date] = None
    ) -> Tuple[StockFinancial, StockFinancial]:
        """Gathers 2 most recent financial filing data for designated ticker

        Args:
            ticker (str): Ticker symbol of the stock.
            api_key (str): API key for Polygon.io.
            query_date (date, optional): Date to query. Defaults to None,
                which queries today's date.
        Returns:
            (StockFinancial, StockFinancial): the most recent financial filing, the previous financial filing
        """

        if self.session is None:
            raise RuntimeError("must use async context manager to initialize client")

        if query_date is None:
            query_date = date.today()

        str_query_date = query_date.strftime("%Y-%m-%d")

        url = "/vX/reference/financials?sort=filing_date"
        url += f"&apiKey={self.api_key}&ticker={ticker}&limit=2&period_of_report_date.lte={str_query_date}"
        try:
            async with self.session.get(url, timeout=self.timeout) as resp:
                response = await resp.json()
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"{ticker}: Timed out while retrieving company financials"
            ) from exc

        if response["status"] == "OK":
            if len(response["results"]) == 0:
                raise ValueError(f"{ticker}: No financials found")

            return StockFinancial.from_dict(
                response["results"][0]
            ), StockFinancial.from_dict(response["results"][1])

        raise ValueError(f"{ticker}: Failed to retrieve company financials")

    async def get_price(self, ticker: str, query_date: Optional[date] = None) -> float:
        """
        Get price for a specified ticker on a specified date
        Args:
            ticker (str): Ticker symbol of the stock.
            query_date (date, optional): Date to query. Defaults to None, which queries today's date.
            timeout (int, optional): time to wait before raising TimeoutError.
        Returns:
            float: Price of the stock on the given date.
        """

        if self.session is None:
            raise RuntimeError("must use async context manager to initialize client")

        # use a different endpoint for current day and past prices
        if query_date is None or query_date == date.today():
            url = f"/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={self.api_key}"
            try:
                async with self.session.get(url, timeout=self.timeout) as resp:
                    response = await resp.json()
                    return response["results"][0]["c"]
            except asyncio.TimeoutError as exc:
                raise TimeoutError(
                    f"{ticker}: Timed out while retrieving price"
                ) from exc
        else:
            str_query_date = query_date.strftime("%Y-%m-%d")
            url = f"/v1/open-close/{ticker}/{str_query_date}?adjusted=true&apiKey={self.api_key}"
            try:
                async with self.session.get(url, timeout=self.timeout) as resp:
                    response = await resp.json()
            except asyncio.TimeoutError as exc:
                raise TimeoutError(
                    f"{ticker}: Timed out while retrieving price"
                ) from exc

            i = 0
            while response["status"] != "OK":
                # markets will not close for more than 3 days at a time
                # if price not found within 3 days, price likely does not exist for that time period
                if i >= 2:
                    raise ValueError(f"Could not find price for {ticker}")

                i += 1
                query_date -= timedelta(days=1)
                str_query_date = query_date.strftime("%Y-%m-%d")

                url = f"/v1/open-close/{ticker}/{str_query_date}?adjusted=true&apiKey={self.api_key}"
                try:
                    async with self.session.get(url, timeout=self.timeout) as resp:
                        response = await resp.json()
                except asyncio.TimeoutError as exc:
                    raise TimeoutError(
                        f"{ticker}: Timed out while retrieving price"
                    ) from exc

            return response["close"]

    async def __aenter__(self):
        self.session = aiohttp.ClientSession("https://api.polygon.io")
        self.active = True
        return self

    async def __aexit__(self, *args: Tuple[Any]):
        assert self.session is not None
        await self.session.close()
        self.active = False
