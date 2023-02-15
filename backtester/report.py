from typing import List

from backtester.models import Trade


class Report:
    def __init__(self, trades: List[List[Trade]]) -> None:
        self.trades = trades

    def to_pdf(self, path: str) -> None:
        """Export report in pdf form"""
        pass

    def print(self) -> None:
        """Print report in text form"""
        print(self.trades)
