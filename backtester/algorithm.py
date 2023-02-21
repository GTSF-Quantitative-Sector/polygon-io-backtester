import asyncio
import logging
import os
from datetime import date
from typing import Any, Coroutine, Dict, List, Tuple

from dateutil.relativedelta import relativedelta
from tqdm import tqdm

import backtester.config
from backtester import async_polygon
from backtester.models import Ticker, TickerDate, Trade
from backtester.report import Report

# TODO: Backtest report creation


class Algorithm:
    """Algorithm base class to extend in order to run backtest"""

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

    def backtest(self, months_back: int = 12) -> Report:
        """Synchronous method for calling the async backtest

        Args:
            months_back (int): how many months to run the backtest over

        Returns:
            List[float]: percentage of initial capital at each timestep
        """

        # needed to run on windows with no warnings
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        return Report(asyncio.run(self._backtest(months_back)))

    async def select_tickers(
        self, ticker_dates: List[TickerDate]
    ) -> List[Tuple[TickerDate, float]]:
        """Specify which tickers to buy in a certain timeslice

        Args:
            ticker_dates (List[TickerDate]): a list of tickers to consider and their associated data
        Returns:
            List[TickerDate]: A list of tickers which have been selected to buy for this timeslice
        """
        raise NotImplementedError(
            "Must implement async select_tickers(self, ticker_dates: List[TickerDate]) -> List[TickerDate] method"
        )

    async def _get_ticker_dates(
        self, client: async_polygon.Client, query_date: date
    ) -> List[TickerDate]:

        """Get TickerDate objects for all considered tickers on a specific query date

        Args:
            client (async_polygon.Client): the async_polygon client to use to make the requests to Polygon.io
            query_date (date): the date for which to query necessary data for
        Returns:
            List[TickerDate]: a list of tickers for which required data was found for the specified query date

        """

        # TODO: Exception handling

        td_coros: List[Coroutine[Any, Any, TickerDate]] = []
        for ticker in self.tickers:
            td_coros.append(client.get_ticker_date(ticker, query_date))

        results: List[TickerDate] = []
        ticker_dates = await asyncio.gather(*td_coros, return_exceptions=True)
        for td in ticker_dates:
            if isinstance(td, Exception):
                self.logger.info(td)
            else:
                results.append(td)

        return results

    async def _backtest(self, months_back: int) -> List[List[Trade]]:

        async with async_polygon.Client(self.API_KEY) as client:

            # gather all ticker data needed for backtest
            curr_date = date.today() - relativedelta(months=months_back)
            data: List[List[TickerDate]] = []

            # allows for lookup of a specific TickerDate for a specific timeslice by Ticker name
            data_lookup: List[Dict[str, TickerDate]] = []
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
        all_trades: List[List[Trade]] = []
        for i in range(months_back - 1):
            # List of Trades for this timeslice
            current_trades: List[Trade] = []

            # get selected tickers to buy for the current time slice
            ticker_quantities = await self.select_tickers(data[i])

            # get the price of each selected ticker for next time period
            for buy_ticker, quantity in ticker_quantities:
                sell_ticker = data_lookup[i + 1][buy_ticker.name]
                t = Trade(buy_ticker, sell_ticker, quantity)
                current_trades.append(t)

            all_trades.append(current_trades)

        return all_trades
