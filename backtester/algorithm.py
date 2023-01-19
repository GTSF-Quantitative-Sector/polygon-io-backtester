import backtester.config
import requests
import bs4 as bs
from typing import List, Tuple
import asyncio
import pandas as pd
import os
from tqdm import tqdm
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

from polygon.rest.models.financials import StockFinancial
from backtester.async_polygon import AsyncPolygon

# TODO: Caching


class Algorithm:

    API_KEY = backtester.config.KEY

    def __init__(self, tickers_and_sectors: List[Tuple[str, str]] = None, verbose: bool = False):
        """
            Initialize a new Algorithm base class

            Args:
                tickers_and_sectors (list[tuple[str, str]]): list of tickers along with their sector to evaluate in the backtest.
                    Defaults to current S&P 500
        """
        self.logger = logging.getLogger("backtester")
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.CRITICAL)

        if not tickers_and_sectors:
            self.logger.debug("Pulling default universe of tickers: current S&P 500")
            tickers_and_sectors = self._get_sp500()        
        
        self.tickers_and_sectors = tickers_and_sectors

    def backtest(self, months_back: int = 12, num_stocks: int = 5) -> list:
        """
            Synchronous method for calling the async backtest

            Args:
                months_back (int): how many months to run the backtest over
                num_stocks (int): how many stocks to select in each period

            Returns:
                list: percentage of initial capital at each timestep
        """

        # weird quirk needed to windows
        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        self.logger.debug("Beginning backtest")
        return asyncio.run(self._backtest(months_back, num_stocks))

    async def score(self, current_financials: StockFinancial, last_financials: StockFinancial, current_price: float):
        """
            Args:
                current_financials (StockFinancial): the most recent company financials
                last_financials (StockFinancial): the previous company financials
                current_price (float): current stock price
        """

        raise NotImplementedError("Must implement score(StockFinancial, StockFinancial, float)")

    async def _rank_tickers(self, client: AsyncPolygon, query_date: str) -> pd.DataFrame:
        """
            Ranks all tickers for a given time period

            Args:
                client (AsyncPolygon): an open Async Polygon connection
                query_date (str): date to evaluate for (yyyy-mm-dd)

            Returns:
                pd.DataFrame: Dataframe containing stock, sector, and score
        """

        results = {}
        tickers = []

        financials_coros = []
        price_coros = []

        # load the coroutines to get financial data for each stock
        for ticker, _ in self.tickers_and_sectors:
            tickers.append(ticker)
            financials_coros.append(client.get_financials(ticker, query_date))

        # load the coroutines to get price for each stock
        for ticker, _ in self.tickers_and_sectors:
            price_coros.append(client.get_price(ticker, query_date))

        # run coroutines
        financials_results = await asyncio.gather(*financials_coros, return_exceptions=True)
        price_results = await asyncio.gather(*price_coros, return_exceptions=True)
        
        ticker_sector_prices = []
        score_coros = []
        for ticker_sector, financials, price in zip(self.tickers_and_sectors, financials_results, price_results):

            # basic error checking
            ticker, sector = ticker_sector
            if isinstance(financials, Exception):
                self.logger.info(f"Could not receive financials for ticker {ticker}")
                continue
            elif isinstance(price, Exception):
                self.logger.info(f"Could not receive price for ticker {ticker}")
                continue
            current_financials, last_financials = financials

            # score stock based on price and financials
            ticker_sector_prices.append((ticker, sector, price))
            score_coros.append(self.score(current_financials, last_financials, price))
            # results[ticker] = (await self.score(current_financials, last_financials, price), sector, price)

        score_results = await asyncio.gather(*score_coros, return_exceptions=True)
        for score, ticker_sector_price in zip(score_results, ticker_sector_prices):
            ticker, sector, price = ticker_sector_price
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
            ticker_df = (await self._rank_tickers(client,  curr_date.strftime("%Y-%m-%d")))[:num_stocks]
            
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
                    price_coros.append(client.get_price(ticker, curr_date.strftime("%Y-%m-%d")))
                prices = await asyncio.gather(*price_coros)

                portfolio_value = 0
                for ticker, price in zip(tickers, prices):
                    portfolio_value += holdings[ticker] * price
                portfolio_values.append(portfolio_value)

                ticker_df = (await self._rank_tickers(client,  curr_date.strftime("%Y-%m-%d")))[:num_stocks]
            
                holdings = {}
                capital_per_stock = 1 / num_stocks

                ticker_df['num_shares'] = capital_per_stock / ticker_df['price']

                for index, row in ticker_df.iterrows():
                    holdings[index] = row['num_shares']

            return portfolio_values

    def _get_sp500(self) -> List[Tuple[str, str]]:
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
            tickers_and_sectors.append((ticker, sector))
        return tickers_and_sectors
