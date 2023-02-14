from dataclasses import dataclass
from datetime import date

from polygon.rest.models.financials import StockFinancial


@dataclass
class Ticker:
    """
    Hold the name and sector of a ticker in a singular class
    """

    name: str
    sector: str

    def __str__(self) -> str:
        return f"{self.name}({self.sector})"

    def __repr__(self) -> str:
        return f"Ticker object({self.name} {self.sector})"


@dataclass
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
