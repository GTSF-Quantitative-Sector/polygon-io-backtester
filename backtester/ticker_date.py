import asyncio
from datetime import date

from backtester.async_polygon import AsyncPolygon, StockFinancial


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
    synced: bool
    _current_financials: StockFinancial
    _last_financials: StockFinancial
    _price: float

    def __init__(self, ticker: Ticker, query_date: date) -> None:
        """
        Args:
            ticker (Ticker): ticker to pull data for
            query_date (datetime.date): date for which to pull data

        """

        self.ticker = ticker
        self.query_date = query_date
        self.synced = False

    async def sync(self, client: AsyncPolygon):
        """
        Synchronize ticker data (price, current_financials, last_financials) for indicated date
        Args:
            client (AsyncPolygon): AsyncPolygon client to use.
                Preferrably the same client across all TickerDates
                so multiple client sessions are not open.
        """

        financials, price = await asyncio.gather(
            client.get_financials(self.ticker.name, self.query_date),
            client.get_price(self.ticker.name, self.query_date),
        )

        self._current_financials, self._last_financials = financials
        self._price = price
        self.synced = True

    @property
    def price(self) -> float:
        if not self.synced:
            raise AttributeError("must sync TickerDate before accessing price")
        return self._price

    @property
    def current_financials(self) -> StockFinancial:
        if not self.synced:
            raise AttributeError(
                "must sync TickerDate before accessing current_financials"
            )
        return self._current_financials

    @property
    def last_financials(self) -> StockFinancial:
        if not self.synced:
            raise AttributeError(
                "must sync TickerDate before accessing last_financials"
            )
        return self._last_financials

    @property
    def name(self) -> str:
        return self.ticker.name

    @property
    def sector(self) -> str:
        return self.ticker.sector

    def __str__(self) -> str:
        return f"{str(self.ticker)} on {self.query_date}"

    def __repr__(self) -> str:
        return f"TickerDate object({self.ticker} on {self.query_date})"