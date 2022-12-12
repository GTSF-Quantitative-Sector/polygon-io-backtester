import aiohttp
from datetime import date, datetime, timedelta
import concurrent
import config
from typing import Tuple

from polygon.rest.models.financials import StockFinancial

API_KEY = config.KEY


class AsyncPolygon:
    """
        Namespace for static methods that are async wrappers over endpoints of the Polygon.io REST API.
        This is designed specifically for the use of the GTSF Investments Committee Quantatative Sector 
        in backtesting value investing strategies, so there are probably a lot of improvements that could be made for a more 
        generalized use case. (i.e. these wrappers do not have the same functionality of the static endpoints rovided by Polygon.io)
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None

    async def get_financials(
            self, ticker: str,
            query_date: str = None,
            timeout: float = 10) -> Tuple[StockFinancial, StockFinancial]:
        """ Gathers 2 most recent financial filing data for designated ticker

        Args:
            ticker (str): Ticker symbol of the stock.
            api_key (str): API key for Polygon.io.
            query_date (str, optional): Date to query. Defaults to None, 
                which queries today's date.
        Returns:
            dict: dictionary containing all available data
        """
    
        if query_date is None:
            query_date = date.today().strftime("%Y-%m-%d")

        URL = "/vX/reference/financials?sort=filing_date"
        URL += f"&apiKey={self.api_key}&ticker={ticker}&limit=2&period_of_report_date.lte={query_date}"
        try:
            async with self.session.get(URL, timeout=timeout) as resp:
                response = await resp.json()
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"{ticker}: Timed out while retrieving company financials")

        if response['status'] == 'OK':
            return StockFinancial.from_dict(response['results'][0]), StockFinancial.from_dict(response['results'][1])
        
        raise ValueError("Failed to retrieve company financials")

    async def get_price(self, ticker: str, query_date: str = None, timeout: float = 10):
        # use a different endpoint for current day and past prices
        if query_date is None or query_date == date.today().strftime("%Y-%m-%d"):
            url = f"/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={self.api_keyapi_key}"

            try:
                async with self.session.get(url, timeout=timeout) as resp:
                    response = await resp.json()
                    return response["results"][0]["c"]
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"{ticker}: Timed out while retrieving price")

        else:
            url = f"/v1/open-close/{ticker}/{query_date}?adjusted=true&apiKey={self.api_key}"
            try:
                async with self.session.get(url, timeout=timeout) as resp:
                    response = await resp.json()
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"{ticker}: Timed out while retrieving price")

            i = 0
            while response["status"] != "OK":
                # markets will not close for more than 3 days at a time
                # if price not found within 3 days, price likely does not exist for that time period
                if i >= 2:
                    raise ValueError(f"Could not find price for {ticker}")
                i += 1
                curr_date = datetime.strptime(query_date, "%Y-%m-%d").date()
                query_date = (curr_date - timedelta(days=1)).strftime("%Y-%m-%d")
                url = f"/v1/open-close/{ticker}/{query_date}?adjusted=true&apiKey={self.api_key}"
                try:
                    async with self.session.get(url, timeout=timeout) as resp:
                        response = await resp.json()
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"{ticker}: Timed out while retrieving price")

            return response["close"]

    async def __aenter__(self):
        self.session = aiohttp.ClientSession("https://api.polygon.io")
        return self

    async def __aexit__(self, *args):
        await self.session.close()
