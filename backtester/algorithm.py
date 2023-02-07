import asyncio
from datetime import date
from dateutil.relativedelta import relativedelta
import logging
import os
from tqdm import tqdm
from typing import List, Tuple, Dict

import backtester.config
from backtester.async_polygon import AsyncPolygon
from backtester.ticker_date import Ticker, TickerDate

# TODO: Backtest report creation


class Algorithm:

    API_KEY = backtester.config.KEY

    def __init__(self, tickers: List[Tuple[str, str]], verbose: bool = False):
        """Initialize a new Algorithm base class

        Args:
            tickers_and_sectors (list[Ticker]): list of Tuples of the form (symbol, sector).
                Universe of tickers to consider in backtest.
        """
        self.logger = logging.getLogger("backtester")
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.CRITICAL)

        self.tickers = [Ticker(symbol, sector) for symbol, sector in tickers]

    def backtest(self, months_back: int = 12) -> list:
        """Synchronous method for calling the async backtest

        Args:
            months_back (int): how many months to run the backtest over

        Returns:
            list: percentage of initial capital at each timestep
        """

        # weird quirk needed to run on windows with no warnings
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        self.logger.debug("Beginning backtest")
        return asyncio.run(self._backtest(months_back))

    async def select_tickers(self, ticker_dates: List[TickerDate]) -> List[TickerDate]:
        """Specify which tickers to buy in a certain timeslice

        Args:
            ticker_dates (List[TickerDate]): a list of all tickers to consider and their associated data
        Returns:
            List[TickerDate]: A list of tickers which have been selected to buy for this timeslice
        """
        raise NotImplementedError(
            "Must implement async select_tickers(self, ticker_dates: List[TickerDate]) -> List[TickerDate] method"
        )

    async def _get_ticker_dates(
        self, client: AsyncPolygon, query_date: date
    ) -> List[TickerDate]:

        coros = []
        ticker_dates = []

        for ticker in self.tickers:
            ticker_date = TickerDate(ticker, query_date)
            ticker_dates.append(ticker_date)
            coros.append(ticker_date.sync(client))

        results = []
        exceptions = await asyncio.gather(*coros, return_exceptions=True)
        for exception, td in zip(exceptions, ticker_dates):
            if exception is None:
                results.append(td)
            else:
                self.logger.info(
                    f"could not retreive info for {td.ticker.name} on {query_date}"
                )

        return results

    async def _backtest(self, months_back: int) -> List[List[TickerDate]]:

        async with AsyncPolygon(self.API_KEY) as client:

            # gather all ticker data needed for backtest
            curr_date = date.today() - relativedelta(months=months_back)
            data = []  # type: List[Dict[str, TickerDate]]
            data_lookup = []
            for _ in tqdm(range(months_back)):
                lookup = {}
                ticker_dates = await self._get_ticker_dates(client, curr_date)
                data.append(ticker_dates)
                for td in ticker_dates:
                    lookup[td.name] = td

                data_lookup.append(lookup)
                curr_date += relativedelta(months=1)

        # calculate portfolio values
        # portfolio starts with 100% value
        portfolio_values = [1.0]
        for i in range(months_back - 1):

            tickers = await self.select_tickers(data[i])
            # calculate holdings for current time period
            holdings = {}
            capital_per_stock = portfolio_values[-1] / len(tickers)
            for ticker in tickers:
                holdings[ticker.name] = capital_per_stock / ticker.price

            # get the price of each selected ticker for next time period
            prices = []
            for td in tickers:
                prices.append(data_lookup[i + 1][td.name].price)

            # calculate the value of the portfolio at the next time period
            portfolio_value = 0
            for ticker, price in zip(tickers, prices):
                portfolio_value += holdings[ticker.name] * price
            portfolio_values.append(portfolio_value)

        return portfolio_values
