class BYYTError(Exception):
    """Base class for classified BYYT upstream failures."""


class BYYTRateLimited(BYYTError):
    """The upstream rejected a query because it was sent too frequently."""


class BYYTUpstreamError(BYYTError):
    """The upstream returned a valid envelope with a failure status."""
