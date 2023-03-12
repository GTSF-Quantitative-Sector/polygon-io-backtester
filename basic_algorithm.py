import json
from typing import List, Tuple

from backtester import Algorithm, TickerDate


class BasicAlgorithm(Algorithm):
    # naively select the first 10 tickers, allocate 1/10th of portfolio to each
    async def select_tickers(
        self, ticker_dates: List[TickerDate]
    ) -> List[Tuple[TickerDate, float]]:
        selections = []
        for t in ticker_dates[:10]:
            selections.append((t, 0.1))

        return selections


if __name__ == "__main__":
    with open("data/sp500.json", "r") as f:
        tickers_and_sectors = json.load(f)

    algo = BasicAlgorithm(tickers_and_sectors)
    report = algo.backtest(36)
    report.print_stats()
    report.export_plot()
    # report.show_plot()
    report.to_pdf()
