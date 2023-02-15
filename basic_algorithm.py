import json
from typing import List

from backtester import Algorithm, TickerDate


class BasicAlgorithm(Algorithm):

    # naively select the first 10 tickers
    async def select_tickers(self, ticker_dates: List[TickerDate]) -> List[TickerDate]:
        return ticker_dates[:10]


if __name__ == "__main__":

    with open("data/sp500.json", "r") as f:
        tickers_and_sectors = json.load(f)

    algo = BasicAlgorithm(tickers_and_sectors, verbose=True)
    print(algo.backtest())
