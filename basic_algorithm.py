import json
from typing import List, Tuple

from backtester import Algorithm, TickerDate


class BasicAlgorithm(Algorithm):

    # naively select the first 10 tickers, buy 5 of each
    async def select_tickers(
        self, ticker_dates: List[TickerDate]
    ) -> List[Tuple[TickerDate, float]]:

        selections = []
        for t in ticker_dates[:10]:
            selections.append((t, 5.0))

        return selections


if __name__ == "__main__":

    with open("data/sp500.json", "r") as f:
        tickers_and_sectors = json.load(f)

    algo = BasicAlgorithm(tickers_and_sectors, verbose=True)
    print(algo.backtest())
