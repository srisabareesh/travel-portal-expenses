"""
Travel type compatibility helpers.

Phase 3.2: the application moved from the legacy
BUSINESS / TRAINING / PROJECT / OTHER travel types to the
new DOMESTIC / INTERNATIONAL travel types.

Historical requests keep their original legacy values: there
is not enough reliable information to classify every
historical request as DOMESTIC or INTERNATIONAL, and no
automatic conversion is performed.

This module is the single source of truth for deciding
whether a travel type value is a legacy (historical) or a
new classification, so that the rest of the application
never hard-codes legacy checks.
"""

from .models import TravelRequest

LEGACY_TRAVEL_TYPES = frozenset(
    {
        TravelRequest.TravelType.BUSINESS,
        TravelRequest.TravelType.TRAINING,
        TravelRequest.TravelType.PROJECT,
        TravelRequest.TravelType.OTHER,
    }
)

NEW_TRAVEL_TYPES = frozenset(
    {
        TravelRequest.TravelType.DOMESTIC,
        TravelRequest.TravelType.INTERNATIONAL,
    }
)


def is_legacy_travel_type(value):
    """
    Return True when the value is one of the
    historical (legacy) travel types.

    Legacy values may exist on historical records but
    must not be used for new requests.
    """

    return value in LEGACY_TRAVEL_TYPES


def is_new_travel_type(value):
    """
    Return True when the value is one of the new
    travel types (DOMESTIC / INTERNATIONAL).
    """

    return value in NEW_TRAVEL_TYPES
