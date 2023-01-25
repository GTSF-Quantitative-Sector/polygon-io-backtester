from backtester import Algorithm, StockFinancial


class BasicAlgorithm(Algorithm):

    async def score(
            self,
            current_financials: StockFinancial,
            last_financials: StockFinancial,
            current_price: float) -> float:

        # rank tickers by current earnings per share
        return current_financials.financials.income_statement.basic_earnings_per_share.value


if __name__ == "__main__":
    algo = BasicAlgorithm(verbose=True)
    print(algo.backtest())
