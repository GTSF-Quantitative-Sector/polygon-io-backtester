from async_polygon import AsyncPolygon, StockFinancial
import asyncio
from datetime import date

class Ticker:

    name: str
    sector: str

    def __init__(self, name: str, sector: str) -> None:
        self.name = name
        self.sector = sector

class TickerDate:

    client: AsyncPolygon
    date: str
    ticker: Ticker
    synced: bool
    _current_financials: StockFinancial
    _last_financials: StockFinancial
    _price: float

    def __init__(self, ticker: Ticker, date: str, client: AsyncPolygon) -> None:
        self.ticker = ticker
        self.date = date
        self.synced = False
        self.client = client

    async def sync(self):
        financials, price = await asyncio.gather(
            self.client.get_financials(self.ticker.name, self.date),
            self.client.get_price(self.ticker.name, self.date),
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
            raise AttributeError("must sync TickerDate before accessing current_financials")
        return self._current_financials

    @property
    def last_financials(self) -> StockFinancial:
        if not self.synced:
            raise AttributeError("must sync TickerDate before accessing last_financials")
        return self._last_financials
