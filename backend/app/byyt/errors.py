class BYYTError(Exception):
    """Base class for classified BYYT upstream failures."""


class BYYTRateLimited(BYYTError):
    """The upstream rejected a query because it was sent too frequently."""


class BYYTUnavailable(BYYTError):
    """The upstream could not be reached or returned a temporary server failure."""


class BYYTUpstreamError(BYYTError):
    """The upstream returned a valid envelope with a failure status."""
