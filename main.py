import asyncio
import os
from datetime import date

from backtester import async_polygon


async def main():

    async with async_polygon.Client("xkkpZQNLtXmSTyJlZT1RpJtpPMG07N4z") as client:
        print(await client.get_price("AAPL", date(2022, 2, 7)))


if __name__ == "__main__":

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
