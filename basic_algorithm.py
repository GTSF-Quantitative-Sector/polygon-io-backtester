from backtester import Algorithm, StockFinancial
import json


class BasicAlgorithm(Algorithm):
    async def score(
        self,
        current_financials: StockFinancial,
        last_financials: StockFinancial,
        current_price: float,
    ) -> float:

        # rank tickers by current earnings per share
        return (
            current_financials.financials.income_statement.basic_earnings_per_share.value
        )


if __name__ == "__main__":

    with open("data/sp500.json", "r") as f:
        tickers_and_sectors = json.load(f)

    algo = BasicAlgorithm(tickers_and_sectors)
    print(algo.backtest())
