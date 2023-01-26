from backtester.config import KEY
from backtester.async_polygon import AsyncPolygon
import asyncio
from datetime import date

async def main():
    async with AsyncPolygon(KEY) as client:
        await client.get_price("AAPL", query_date=date(2020,10,28))

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())