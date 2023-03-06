import asyncio
from typing import List, cast

import pandas as pd

from . import async_polygon
from .config import KEY
from .models import TradeTimeSlice


class Report:
    def __init__(self, trades: List[TradeTimeSlice]) -> None:
        self.all_trades = trades

    def to_pdf(self, path: str) -> None:
        """Export report in pdf form"""
        pass

    def print(self) -> None:
        """Print report in text form"""
        print(asyncio.run(self.get_portfolio_values_vs_spy()))

    async def get_portfolio_values_vs_spy(self) -> pd.DataFrame:
        """Return a dataframe of daily portfolio values and sp500 values"""
        timeslice_values_tasks = []
        async with async_polygon.Client(KEY) as client:
            # global start and end dates
            start_date = self.all_trades[0].start
            end_date = self.all_trades[-1].end

            # download value for each timeslice
            for timeslice in self.all_trades:
                timeslice_values_tasks.append(
                    asyncio.create_task(self.get_timeslice_values(timeslice, client))
                )

            # wait for timeslice values, while downloading spy values
            spy_values, *timeslice_values = await asyncio.gather(
                client.get_daily_prices("SPY", start_date, end_date),
                *timeslice_values_tasks
            )

            # adjust timeslice values to account for previous timeslices
            for i in range(len(timeslice_values) - 1):
                previous_end_value = timeslice_values[i][-1]
                timeslice_values[i + 1] *= previous_end_value

            # normalize spy
            spy_values /= spy_values[0]

            # concatenate all timeslice values
            portfolio_values = pd.concat(timeslice_values)
            portfolio_values = portfolio_values[
                ~portfolio_values.index.duplicated(keep="first")
            ]

            return pd.DataFrame({"Strategy": portfolio_values, "SPY": spy_values})

    async def get_timeslice_values(
        self, timeslice: TradeTimeSlice, client: async_polygon.Client
    ) -> pd.Series:
        """Get portfolio values for a particular timeslice"""

        # retrieve initial prices for this timeslice
        starting_price_tasks = []
        for trade in timeslice.trades:
            starting_price_tasks.append(
                asyncio.create_task(client.get_price(trade.name, timeslice.start))
            )

        # determine the quantities each stock will be bought at
        quantities = []
        excess_capital = 1  # proportion of capital remaining in cash
        starting_prices = await asyncio.gather(*starting_price_tasks)
        for trade, starting_price in zip(timeslice.trades, starting_prices):
            quantities.append(trade.proportion_of_capital / starting_price)
            excess_capital -= trade.proportion_of_capital

        # get prices for each ticker in portfolio over the course of this timeslice
        trade_price_tasks = []
        for trade in timeslice.trades:
            trade_price_tasks.append(
                asyncio.create_task(
                    client.get_daily_prices(trade.name, trade.start, trade.end)
                )
            )

        trade_prices = await asyncio.gather(*trade_price_tasks)
        for quantity, prices in zip(quantities, trade_prices):
            prices *= quantity

        # scale by quantities
        return cast(pd.Series, sum(trade_prices) + excess_capital)
