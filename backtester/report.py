import asyncio
from datetime import date, datetime
from typing import List, Tuple, cast

import matplotlib.pyplot as plt
import pandas as pd

from . import async_polygon
from .config import KEY
from .models import TradeTimeSlice

import jinja2
import pdfkit

import os
from sys import platform

class Report:
    def __init__(self, timeslices: List[TradeTimeSlice]) -> None:
        self.timeslices = timeslices
        self.portfolio_values = asyncio.run(self.get_portfolio_values_vs_spy())

    def to_pdf(self, path: str = "") -> None:
        """Export report in pdf form"""

        # Get the path to the working directory
        path_to_directory = os.path.dirname(os.path.abspath(__name__))
        # Add a \ if windows, else add /
        path_to_directory += "\\" if platform == "win32" else "/"

        strategy_sharpe, spy_sharpe = self.calculate_annualized_sharpe_ratio()
        strategy_vol, spy_vol = self.calculate_volatility()
        context = {
            "plot": "test plot",
            "cumulative_returns": f"{self.calculate_cumulative_return():.5f}",
            "cagr": f"{self.calculate_cagr():.5f}",
            "beta": f"{self.calculate_beta():.5f}",
            "correlation": f"{self.calculate_correlation():.5f}",
            "strategy_sharpe": f"{strategy_sharpe:.5f}",
            "spy_sharpe": f"{spy_sharpe:.5f}",
            "strategy_vol": f"{strategy_vol:.5f}",
            "spy_vol": f"{spy_vol:.5f}",
            "path": path_to_directory,
            "date": str(datetime.now().strftime("%b %d, %Y")),
        }

        # Create an environment for out template and export the PDF
        template_loader = jinja2.FileSystemLoader("./")
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template("report-template.html")
        output_text = template.render(context)

        # config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
        pdfkit.from_string(output_text, 'report.pdf', options={"enable-local-file-access": ""})

    def print_stats(self) -> None:
        """Print report in text form"""

        print(f"Cumulative Returns: {self.calculate_cumulative_return():.5f}")
        print(f"CAGR: {self.calculate_cagr():.5f}")
        print(f"Beta: {self.calculate_beta():.5f}")
        print(f"Correlation: {self.calculate_correlation():.5f}")
        strategy_sharpe, spy_sharpe = self.calculate_annualized_sharpe_ratio()
        print(f"Strategy Sharpe {strategy_sharpe:.5f} | SPY Sharpe {spy_sharpe:.5f}")
        strategy_vol, spy_vol = self.calculate_volatility()
        print(f"Strategy Vol: {strategy_vol:.5f} | SPY Vol: {spy_vol:.5f}")

    def show_plot(self) -> None:
        self.portfolio_values.plot.line()
        plt.show()

    def export_plot(self) -> None:
        self.portfolio_values.plot.line()
        plt.savefig("plot.png", bbox_inches="tight")

    def calculate_beta(self) -> float:
        weekly_returns = self.portfolio_values.iloc[::5, :].pct_change(periods=1)[1:]
        covariance = weekly_returns.cov()
        return covariance["Strategy"]["SPY"] / covariance["SPY"]["SPY"]

    def calculate_correlation(self) -> float:
        weekly_returns = self.portfolio_values.iloc[::5, :].pct_change(periods=1)[1:]
        return weekly_returns.corr()["Strategy"]["SPY"]

    def calculate_volatility(self) -> Tuple[float, float]:
        weekly_returns = self.portfolio_values.iloc[::5, :].pct_change(periods=1)[1:]
        std = weekly_returns.std()
        return std["Strategy"], std["SPY"]

    def calculate_cumulative_return(self) -> float:
        starting_value = self.portfolio_values["Strategy"][0]
        ending_value = self.portfolio_values["Strategy"][-1]
        return (ending_value - starting_value) / starting_value

    def calculate_cagr(self) -> float:
        starting_value = self.portfolio_values["Strategy"][0]
        ending_value = self.portfolio_values["Strategy"][-1]

        # resolve type hinting
        start_date = cast(date, self.portfolio_values.index[0])
        end_date = cast(date, self.portfolio_values.index[-1])
        diff = (end_date - start_date).days / 365.25

        return (ending_value / starting_value) ** (1 / diff) - 1

    def calculate_annualized_sharpe_ratio(self) -> Tuple[float, float]:
        # TODO: Find source for risk free rate

        weekly_returns = self.portfolio_values.iloc[::5, :].pct_change(periods=1)[1:]
        weekly_sharpe = weekly_returns.mean() / weekly_returns.std()
        annualized_sharpe = (52.1429**0.5) * weekly_sharpe
        return annualized_sharpe["Strategy"], annualized_sharpe["SPY"]

    async def get_portfolio_values_vs_spy(self) -> pd.DataFrame:
        """Return a dataframe of daily portfolio values and sp500 values"""
        timeslice_values_tasks = []
        async with async_polygon.Client(KEY) as client:
            # global start and end dates
            start_date = self.timeslices[0].start
            end_date = self.timeslices[-1].end

            # download value for each timeslice
            for timeslice in self.timeslices:
                timeslice_values_tasks.append(
                    asyncio.create_task(self.get_timeslice_values(timeslice, client))
                )

            # wait for timeslice values, while downloading spy values
            spy_values, *timeslice_values = await asyncio.gather(
                client.get_daily_prices("SPY", start_date, end_date),
                *timeslice_values_tasks,
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
