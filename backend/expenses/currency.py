"""
Centralized currency list for the expenses module.

This is the single source of truth for every currency the
application accepts: expense entries, expense
configuration and settlements all validate against it.
The frontend dropdown mirrors this list; the backend
remains the authority.
"""

from django.core.exceptions import ValidationError

CURRENCIES = (
    "INR",
    "USD",
    "EUR",
    "GBP",
    "AED",
    "SGD",
    "AUD",
    "CAD",
    "JPY",
)

CURRENCY_CHOICES = tuple(
    (code, code) for code in CURRENCIES
)

CURRENCY_ERROR_MESSAGE = (
    "Currency must be one of: "
    + ", ".join(CURRENCIES)
    + "."
)


def validate_currency(value):
    """
    Validate an ISO code against the centralized list.
    Raises ValidationError for anything else.

    An empty value is left to the caller to treat as
    optional or required.
    """

    if not value:
        return value

    normalized = str(value).strip().upper()

    if normalized not in CURRENCIES:
        raise ValidationError(CURRENCY_ERROR_MESSAGE)

    return normalized
