class InvalidAPIKeyError(Exception):
    """Polgon could not recognize API Key"""

    pass


class PriceNotFoundError(Exception):
    """Could not find price for given ticker"""

    pass


class FinancialsNotFoundError(Exception):
    """Could not find 2 most recent financial filings"""

    pass
