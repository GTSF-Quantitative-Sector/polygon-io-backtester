from backtester.config import KEY
from backtester.async_polygon import AsyncPolygon
import asyncio

async def main():
    async with AsyncPolygon(KEY) as client:
        await client.get_financials("AAPL")

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())