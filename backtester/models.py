from dataclasses import dataclass
from datetime import date

from polygon.rest.models.financials import StockFinancial


@dataclass(frozen=True)
class Ticker:
    """
    Hold the name and sector of a ticker in a singular class
    """

    name: str
    sector: str

    def __str__(self) -> str:
        return f"{self.name}({self.sector})"


@dataclass(frozen=True)
class TickerDate:
    """
    Class to contain information for a ticker on a specific date.
    Includes price and current/last financials
    """

    ticker: Ticker
    query_date: date
    current_financials: StockFinancial
    last_financials: StockFinancial
    price: float

    @property
    def name(self) -> str:
        """Ticker name"""
        return self.ticker.name

    @property
    def sector(self) -> str:
        """Ticker sector"""
        return self.ticker.sector

    def __repr__(self) -> str:
        return f"TickerDate(name: {self.name}, sector: {self.sector}, date: {self.query_date})"


@dataclass
class Trade:
    buy_ticker_date: TickerDate
    sell_ticker_date: TickerDate
    quantity: float

    def __repr__(self) -> str:
        return f"Trade(buyTicker: {self.buy_ticker_date.__repr__()}, sellTicker: {self.sell_ticker_date.__repr__()})"
