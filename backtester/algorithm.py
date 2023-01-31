import asyncio
from datetime import date
from dateutil.relativedelta import relativedelta
import logging
import os
from tqdm import tqdm
from typing import List, Tuple

import backtester.config
from backtester.async_polygon import AsyncPolygon
from backtester.ticker_date import Ticker, TickerDate
from polygon.rest.models.financials import StockFinancial

# TODO: Backtest report creation


class Algorithm:

    API_KEY = backtester.config.KEY

    def __init__(self, tickers: List[Tuple[str, str]], verbose: bool = False):
        """
        Initialize a new Algorithm base class

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

    def backtest(self, months_back: int = 12, num_stocks: int = 5) -> list:
        """
        Synchronous method for calling the async backtest

        Args:
            months_back (int): how many months to run the backtest over
            num_stocks (int): how many stocks to select in each period

        Returns:
            list: percentage of initial capital at each timestep
        """

        # weird quirk needed to run on windows with no warnings
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        self.logger.debug("Beginning backtest")
        return asyncio.run(self._backtest(months_back, num_stocks))

    async def score(
        self,
        current_financials: StockFinancial,
        last_financials: StockFinancial,
        current_price: float,
    ) -> float:
        """
        Args:
            current_financials (StockFinancial): the most recent company financials
            last_financials (StockFinancial): the previous company financials
            current_price (float): current stock price
        Returns:
            float: a rating for the current stock. Higher = more preferrable and
                will be selected by the backtest
        """

        raise NotImplementedError(
            "Must implement score(StockFinancial, StockFinancial, float)"
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

    def _group_by_sort(
        self, ticker_scores: List[Tuple[TickerDate, float]]
    ) -> List[TickerDate]:
        """
        Takes in list of TickerDates and their respective scores, selects the
            highest scoring ticker from each sector, and sorts the top scorers in each sector.
        Args:
            ticker_scores (List[Tuple[TickerDate, float]]): List of TickerDates and respective scores
        """

        sector_max = {}
        for ticker_date, score in ticker_scores:
            if ticker_date.sector not in sector_max.keys():
                sector_max[ticker_date.sector] = (ticker_date, score)
            else:
                _, curr_high_score = sector_max[ticker_date.sector]
                if score > curr_high_score:
                    sector_max[ticker_date.sector] = (ticker_date, score)

        sector_maxes = list(sector_max.values())
        sector_maxes.sort(key=lambda x: x[1], reverse=True)
        return [i[0] for i in sector_maxes]

    async def _rank_tickers(
        self, ticker_dates: List[TickerDate], num_stocks: int
    ) -> List[TickerDate]:
        """
        Ranks all tickers for a given time period

        Args:
            ticker_dates (list(TickerDate)): stock ticker/data objects to rank
                (based on score method)

        Returns:
            pd.DataFrame: Dataframe containing stock, sector, and score (sorted)
        """

        score_coros = []
        for ticker_date in ticker_dates:
            current_financials = ticker_date.current_financials
            last_financials = ticker_date.last_financials
            price = ticker_date.price
            score_coros.append(self.score(current_financials, last_financials, price))

        ticker_score = []
        score_results = await asyncio.gather(*score_coros, return_exceptions=True)
        for score, ticker_date in zip(score_results, ticker_dates):
            price = ticker_date.price

            if isinstance(score, NotImplementedError):
                raise NotImplementedError(
                    "must implement async score(self, current_financials: StockFinancial, last_financials: StockFinancial, current_price: float)"
                )
            elif isinstance(score, Exception):
                self.logger.info(f"Could not score ticker {ticker_date.name}")
                continue

            ticker_score.append((ticker_date, score))

        return self._group_by_sort(ticker_score)[:num_stocks]

    async def _backtest(self, months_back: int, num_stocks: int) -> List[float]:
        async with AsyncPolygon(self.API_KEY) as client:
            portfolio_values = [1.0]

            curr_date = date.today() - relativedelta(months=months_back)
            tickers = await self._rank_tickers(
                await self._get_ticker_dates(client, curr_date), num_stocks
            )

            holdings = {}
            capital_per_stock = portfolio_values[-1] / num_stocks
            for ticker in tickers:
                holdings[ticker.name] = capital_per_stock / ticker.price

            for _ in tqdm(range(months_back - 1)):
                curr_date += relativedelta(months=1)

                price_coros = []
                for ticker_name in holdings.keys():
                    price_coros.append(client.get_price(ticker_name, curr_date))
                prices = await asyncio.gather(*price_coros)

                portfolio_value = 0
                for ticker, price in zip(tickers, prices):
                    portfolio_value += holdings[ticker.name] * price
                portfolio_values.append(portfolio_value)

                tickers = await self._rank_tickers(
                    await self._get_ticker_dates(client, curr_date), num_stocks
                )
                holdings = {}
                capital_per_stock = portfolio_values[-1] / num_stocks
                for ticker in tickers:
                    holdings[ticker.name] = capital_per_stock / ticker.price

        return portfolio_values
