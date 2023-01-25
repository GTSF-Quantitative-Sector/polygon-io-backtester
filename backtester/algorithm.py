import backtester.config
import requests
import bs4 as bs
from typing import List
import asyncio
import pandas as pd
import os
from tqdm import tqdm
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging

from polygon.rest.models.financials import StockFinancial
from backtester.async_polygon import AsyncPolygon
from backtester.ticker_date import Ticker, TickerDate

# TODO: Caching


class Algorithm:

    API_KEY = backtester.config.KEY

    def __init__(self, tickers: List[Ticker] = None, verbose: bool = False):
        """
            Initialize a new Algorithm base class

            Args:
                tickers_and_sectors (list[Ticker]): list of Ticker (ticker_date.py) objects containing ticker name and sector.
                    Universe of tickers to consider in backtest. Defaults to current S&P 500.
        """
        self.logger = logging.getLogger("backtester")
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.CRITICAL)

        if not tickers:
            self.logger.debug("Pulling default universe of tickers: current S&P 500")
            tickers = self._get_sp500()        
        
        self.tickers = tickers

    def backtest(self, months_back: int = 12, num_stocks: int = 5) -> list:
        """
            Synchronous method for calling the async backtest

            Args:
                months_back (int): how many months to run the backtest over
                num_stocks (int): how many stocks to select in each period

            Returns:
                list: percentage of initial capital at each timestep
        """

        # weird quirk needed for windows
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        self.logger.debug("Beginning backtest")
        return asyncio.run(self._backtest(months_back, num_stocks))

    async def score(
            self, 
            current_financials: StockFinancial,
            last_financials: StockFinancial,
            current_price: float) -> float:
        """
            Args:
                current_financials (StockFinancial): the most recent company financials
                last_financials (StockFinancial): the previous company financials
                current_price (float): current stock price
        """

        raise NotImplementedError("Must implement score(StockFinancial, StockFinancial, float)")

    async def _get_ticker_dates(self, client: AsyncPolygon, query_date: date) -> List[TickerDate]:
        coros = []
        ticker_dates = []

        for ticker in self.tickers:
            ticker_date = TickerDate(ticker, query_date, client)
            ticker_dates.append(ticker_date)
            coros.append(ticker_date.sync())

        exceptions = await asyncio.gather(*coros, return_exceptions=True)
        results = []
        for exception, td in zip(exceptions, ticker_dates):
            if exception is None:
                results.append(td)
            else:
                self.logger.info(f"could not retreive info for {td.ticker.name} on {query_date}")

        return results

    async def _rank_tickers(self, ticker_dates: List[TickerDate]) -> pd.DataFrame:
        """
            Ranks all tickers for a given time period

            Args:
                ticker_dates (list(TickerDate)): stock ticker/data objects to rank
                    (based on score method)

            Returns:
                pd.DataFrame: Dataframe containing stock, sector, and score (sorted)
        """

        results = {}
        score_coros = []
        for ticker_date in ticker_dates:
            current_financials = ticker_date.current_financials
            last_financials = ticker_date.last_financials
            price = ticker_date.price
            score_coros.append(self.score(current_financials, last_financials, price))
        
        score_results = await asyncio.gather(*score_coros, return_exceptions=True)
        for score, ticker_date in zip(score_results, ticker_dates):
            ticker = ticker_date.ticker.name
            sector = ticker_date.ticker.sector

            if isinstance(score, NotImplementedError):
                raise NotImplementedError("must implement async score(self, current_financials: StockFinancial, last_financials: StockFinancial, current_price: float)")
            elif isinstance(score, Exception):
                self.logger.info(f"Could not score ticker {ticker}")
                continue

            results[ticker] = (score, sector, price)        

        # load into df
        df = pd.DataFrame.from_dict(results, orient="index", columns=["score", "sector", "price"])
        df = df.sort_values(by="score", ascending=False)
        return df

    async def _backtest(self, months_back: int, num_stocks: int):
        async with AsyncPolygon(self.API_KEY) as client:
            portfolio_values = [1]

            curr_date = datetime.now() - relativedelta(months=months_back)
            ticker_df = (
                await self._rank_tickers(
                    await self._get_ticker_dates(client, curr_date)))[:num_stocks]
            
            holdings = {}
            capital_per_stock = 1 / num_stocks

            ticker_df['num_shares'] = capital_per_stock / ticker_df['price']

            for index, row in ticker_df.iterrows():
                holdings[index] = row['num_shares']

            for _ in tqdm(range(months_back-1)):
                curr_date += relativedelta(months=1)
                
                price_coros = []
                tickers = []
                for ticker in holdings.keys():
                    tickers.append(ticker)
                    price_coros.append(client.get_price(ticker, curr_date))
                prices = await asyncio.gather(*price_coros)

                portfolio_value = 0
                for ticker, price in zip(tickers, prices):
                    portfolio_value += holdings[ticker] * price
                portfolio_values.append(portfolio_value)

                ticker_df = (
                    await self._rank_tickers(
                        await self._get_ticker_dates(client, curr_date)))[:num_stocks]
            
                holdings = {}
                capital_per_stock = 1 / num_stocks

                ticker_df['num_shares'] = capital_per_stock / ticker_df['price']

                for index, row in ticker_df.iterrows():
                    holdings[index] = row['num_shares']

            return portfolio_values

    def _get_sp500(self) -> List[Ticker]:
        """Get a list of tickers and their sectors for all stocks in the S&P 500.

        Returns:
            List[Tuple[str, str]]: List of tuples containing ticker and sector.
        """
        url = "http://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(url)
        source = bs.BeautifulSoup(response.text, "lxml")
        table = source.find("table", {"class": "wikitable sortable"})
        tickers_and_sectors = []
        for row in table.findAll("tr")[1:]:
            ticker = row.findAll("td")[0].text.replace("\n", "")
            sector = row.findAll("td")[3].text.replace("\n", "")
            tickers_and_sectors.append(Ticker(ticker, sector))

        return tickers_and_sectors
