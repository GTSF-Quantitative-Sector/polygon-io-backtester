class InvalidAPIKeyError(Exception):
    """Polgon could not recognize API Key"""


class PriceNotFoundError(Exception):
    """Could not find price for given ticker"""


class FinancialsNotFoundError(Exception):
    """Could not find 2 most recent financial filings"""


class InvalidStockSelectionError(Exception):
    """Did not return a valid selection of stocks"""
