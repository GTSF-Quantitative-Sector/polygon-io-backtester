import asyncio
import os

from .algorithm import Algorithm, TickerDate
from .models import StockFinancial

# needed to run on windows with no warnings
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
