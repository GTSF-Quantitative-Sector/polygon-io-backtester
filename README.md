# Polygon.io Backtester
This is an extension of a project built with Locke Adams for the GTSF Investments Committee Quantatative Sector. This semster (Fall 2022), the Quant Sector partnered with [Polygon.io](https://polygon.io/) for our data needs. In developing value investing strategies based on data fatched from Polygon, we found that using naive synchronous calls to their REST API or using their provided Python client was far to slow to perform backtests in a reasonable time period. For example, for a 24-month backtest on the S&P 500, with holdings recalculated every month, there would be 500*24 calls to get stock price and 500*8 to get the quarterly financials (assuming proper caching of past calls to the financials API, which proved hard to accomplish). If these calls are run in a synchronous fashion, backtests can take hours to perform, even over this relatively short 24 month window. \
\
So, we decided to create a generalizable backtesting framework which completely abstracts asynchronous API calls away from the user. As a result, the framework only requires the user to provide a function to score a stock based on current quarterly financials, past quarterly financials, and current price. NOTE: these inputs are currently sufficient for our uses, but for any trading strategy that trades on a frequency lower than 1 month this is probably not enough information. In having a constant frame of information provided to the user, this program is able to optimize that same 24-month backtest down to under 1 minute. \
\
There are still some shortcomings that must be addressed, for example the universe of equities considered is only the current S&P 500, which would not have been known at the time of the backtest, and right now the framework assumes complete freedom over fractional shares. All in all, though, this framework does provide a good starting point for intuition about whether the model will be successful.

## Installation
To install, clone this repository, then run
```
pip install -r requirements.txt
```
Additionally, you must create a `config.py` file in the backtester directory with format 

```
KEY="API Key here"
```

## Quick Example
A new algorithm is definied by extending the Algorithm class and implementing the score method. The score method takes two `StockFinancial` objects, defined by the Polygon.io Python client [here](https://github.com/polygon-io/client-python/blob/master/polygon/rest/models/financials.py), to represent the current and last financial statements, and the current price. The method is async, which can be leveraged to optimize the backtest if the user needs to pull in any additional information from other sources
```
from backtester import Algorithm, StockFinancial


class BasicAlgorithm(Algorithm):

    async def score(self, current_financials: StockFinancial, last_financials: StockFinancial, current_price: float):
        # rank tickers by current earnings per share
        return current_financials.financials.income_statement.basic_earnings_per_share.value

if __name__ == "__main__":
    algo = BasicAlgorithm(verbose=True)
    print(algo.backtest())
```
