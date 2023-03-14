import asyncio
import logging
from datetime import date
from typing import List, Tuple

from dateutil.relativedelta import relativedelta
from tqdm import tqdm

from . import async_polygon
from .config import KEY
from .exceptions import (FinancialsNotFoundError, InvalidStockSelectionError,
                         PriceNotFoundError)
from .models import Ticker, TickerDate, Trade, TradeTimeSlice
from .report import Report

# TODO: Backtest report creation


class Algorithm:
    """Algorithm base class to extend in order to run backtest"""

    API_KEY = KEY

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

        return Report(asyncio.run(self._backtest(months_back)), months_back)

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

        # ensure the market is open on the given day
        while await client.market_is_closed(query_date):
            query_date -= relativedelta(days=1)

        td_tasks: List[asyncio.Task[TickerDate]] = []
        for ticker in self.tickers:
            td_tasks.append(
                asyncio.create_task(client.get_ticker_date(ticker, query_date))
            )

        results: List[TickerDate] = []
        for td in await asyncio.gather(*td_tasks, return_exceptions=True):
            if isinstance(td, PriceNotFoundError):
                self.logger.info(td)
            elif isinstance(td, FinancialsNotFoundError):
                self.logger.info(td)
            elif isinstance(td, Exception):
                raise td
            else:
                results.append(td)

        return results

    async def _backtest(self, months_back: int) -> List[TradeTimeSlice]:
        async with async_polygon.Client(self.API_KEY) as client:
            # gather all ticker data needed for backtest
            curr_date = date.today() - relativedelta(months=months_back)
            data: List[List[TickerDate]] = []

            print("downloading data...")
            for _ in tqdm(range(months_back + 1)):
                ticker_dates = await self._get_ticker_dates(client, curr_date)
                data.append(ticker_dates)
                curr_date += relativedelta(months=1)

        all_trades: List[TradeTimeSlice] = []
        for i in range(months_back):
            start_date = data[i][0].query_date
            end_date = data[i + 1][0].query_date

            # List of Trades for this timeslice
            current_trades = TradeTimeSlice(start_date, end_date)

            # get selected tickers to buy for the current time slice
            ticker_quantities = await self.select_tickers(data[i])

            # get the price of each selected ticker for next time period
            total_capital = 0
            for buy_ticker, proportion_of_capital in ticker_quantities:
                current_trades.add_trade(
                    Trade(
                        name=buy_ticker.name,
                        proportion_of_capital=proportion_of_capital,
                        start=buy_ticker.query_date,
                        end=end_date,
                    )
                )
                total_capital += proportion_of_capital

            if total_capital > 1:
                raise InvalidStockSelectionError(
                    "Cannot allocate more than 100% of portfolio"
                )

            all_trades.append(current_trades)

        return all_trades
