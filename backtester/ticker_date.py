from datetime import date

from polygon.rest.models.financials import StockFinancial


class Ticker:
    """
    Hold the name and sector of a ticker in a singular class
    """

    name: str
    sector: str

    def __init__(self, name: str, sector: str) -> None:
        """
        Args:
            name (str): ticker name
            sector (str): sector to classify the ticker in
        """
        self.name = name
        self.sector = sector

    def __str__(self) -> str:
        return f"{self.name}({self.sector})"

    def __repr__(self) -> str:
        return f"Ticker object({self.name} {self.sector})"


class TickerDate:
    """
    Class to contain information for a ticker on a specific date.
    Includes price and current/last financials
    """

    query_date: date
    ticker: Ticker
    current_financials: StockFinancial
    last_financials: StockFinancial
    price: float

    def __init__(
        self,
        ticker: Ticker,
        query_date: date,
        current_financials: StockFinancial,
        last_financials: StockFinancial,
        price: float,
    ) -> None:
        """
        Args:
            ticker (Ticker): ticker to pull data for
            query_date (datetime.date): date for which to pull data
            current_financials (StockFinancial): most recent financial filing
            last_financials (StockFinancial): previous financial filing
            price (float): stock price on this date

        """

        self.ticker = ticker
        self.query_date = query_date
        self.current_financials = current_financials
        self.last_financials = last_financials
        self.price = price

    @property
    def name(self):
        return self.ticker.name

    @property
    def sector(self):
        return self.ticker.sector
