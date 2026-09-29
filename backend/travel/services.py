"""
Travel type and status compatibility helpers.

Phase 3.2: the application moved from the legacy
BUSINESS / TRAINING / PROJECT / OTHER travel types to the
new DOMESTIC / INTERNATIONAL travel types.

Historical requests keep their original legacy values: there
is not enough reliable information to classify every
historical request as DOMESTIC or INTERNATIONAL, and no
automatic conversion is performed.

Phase 3.3: the request lifecycle was extended with new
workflow statuses. Historical records keep their legacy
statuses; the new statuses exist so that later workflow
phases can drive requests through them.

This module is the single source of truth for deciding
whether a travel type or status value is a legacy
(historical) or a new classification, and for the workflow
definitions shared by both travel types, so that the rest
of the application never hard-codes legacy checks.
"""

from .models import TravelRequest

# ==========================================================
# Travel type compatibility (Phase 3.2)
# ==========================================================

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


# ==========================================================
# Status compatibility (Phase 3.3)
# ==========================================================

Status = TravelRequest.Status

LEGACY_STATUSES = frozenset(
    {
        Status.DRAFT,
        Status.SUBMITTED,
        Status.DOCUMENT_PENDING,
        Status.DOCUMENT_VERIFICATION,
        Status.APPROVED,
        Status.REJECTED,
        Status.CANCELLED,
    }
)

NEW_STATUSES = frozenset(
    {
        ##Shared lifecycle stages (DRAFT and SUBMITTED are
        ##legacy values shared with the new workflows and
        ##are not repeated here).
        Status.MANAGER_APPROVAL,
        Status.MANAGER_APPROVED,
        Status.TRAVEL_BOOKING,
        Status.TRAVEL_BOOKED,
        Status.TRAVEL_IN_PROGRESS,
        Status.EXPENSE_SUBMISSION,
        Status.EXPENSE_VERIFICATION,
        Status.SETTLEMENT_PENDING,
        Status.SETTLEMENT_APPROVAL,
        Status.SETTLEMENT_APPROVED,
        Status.SETTLEMENT_PROCESSING,
        Status.COMPLETED,
        Status.CLOSED,
        ##International-specific statuses.
        Status.DOCUMENTS_PENDING,
        Status.DOCUMENTS_UNDER_REVIEW,
        Status.VISA_PROCESSING,
        Status.VISA_APPROVED,
        ##Exception statuses.
        Status.REQUEST_REJECTED,
        Status.REQUEST_CANCELLED,
    }
)


def is_legacy_status(status):
    """
    Return True when the value is one of the
    historical (legacy) request statuses.

    Legacy values may exist on historical records but
    are never assigned to requests that enter the
    new workflows.
    """

    return status in LEGACY_STATUSES


def is_new_status(status):
    """
    Return True when the value is one of the new
    workflow statuses (including the exception
    statuses REQUEST_REJECTED / REQUEST_CANCELLED).
    """

    return status in NEW_STATUSES


# ----------------------------------------------------------
# Status families / equivalence.
#
# Legacy and new statuses that mean the same business thing
# are grouped into shared families. This is classification
# only: values are never converted into one another.
#
# DOCUMENT_PENDING      <-> DOCUMENTS_PENDING
# DOCUMENT_VERIFICATION <-> DOCUMENTS_UNDER_REVIEW
# APPROVED              <-> MANAGER_APPROVED
# REJECTED              <-> REQUEST_REJECTED
# CANCELLED             <-> REQUEST_CANCELLED
# ----------------------------------------------------------

DOCUMENTS_FAMILY = "DOCUMENTS"

DOCUMENTS_FAMILY_MEMBERS = frozenset(
    {
        Status.DOCUMENT_PENDING,
        Status.DOCUMENTS_PENDING,
    }
)

DOCUMENT_REVIEW_FAMILY = "DOCUMENT_REVIEW"

DOCUMENT_REVIEW_FAMILY_MEMBERS = frozenset(
    {
        Status.DOCUMENT_VERIFICATION,
        Status.DOCUMENTS_UNDER_REVIEW,
    }
)

DECISION_FAMILY = "DECISION"

DECISION_FAMILY_MEMBERS = frozenset(
    {
        Status.APPROVED,
        Status.MANAGER_APPROVED,
    }
)

REJECTION_FAMILY = "REJECTION"

REJECTION_FAMILY_MEMBERS = frozenset(
    {
        Status.REJECTED,
        Status.REQUEST_REJECTED,
    }
)

CANCELLATION_FAMILY = "CANCELLATION"

CANCELLATION_FAMILY_MEMBERS = frozenset(
    {
        Status.CANCELLED,
        Status.REQUEST_CANCELLED,
    }
)

STATUS_FAMILY_MAP = {
    **{
        status: DOCUMENTS_FAMILY
        for status in DOCUMENTS_FAMILY_MEMBERS
    },
    **{
        status: DOCUMENT_REVIEW_FAMILY
        for status in DOCUMENT_REVIEW_FAMILY_MEMBERS
    },
    **{
        status: DECISION_FAMILY
        for status in DECISION_FAMILY_MEMBERS
    },
    **{
        status: REJECTION_FAMILY
        for status in REJECTION_FAMILY_MEMBERS
    },
    **{
        status: CANCELLATION_FAMILY
        for status in CANCELLATION_FAMILY_MEMBERS
    },
}

EXCEPTION_STATUS_FAMILIES = frozenset(
    {
        REJECTION_FAMILY,
        CANCELLATION_FAMILY,
    }
)


def status_family(status):
    """
    Return the business family the status belongs to, or
    None when the status does not participate in a
    legacy/new equivalence.

    Families let future phases compare or group statuses
    without hard-coding individual values in views.
    """

    return STATUS_FAMILY_MAP.get(status)


def is_exception_status(status):
    """
    Return True when the status is one of the terminal
    exception outcomes (rejection or cancellation) in
    either the legacy or the new vocabulary.
    """

    family = status_family(status)

    return (
        family is not None
        and family in EXCEPTION_STATUS_FAMILIES
    )


# ==========================================================
# Workflow definitions (Phase 3.3)
#
# Declarative lifecycle definitions for later workflow
# phases. No view or service currently transitions requests
# through these statuses; wiring them in belongs to later
# phases.
#
# DRAFT and SUBMITTED are shared by both workflows and are
# legacy values reused by the new lifecycles.
# ==========================================================

DOMESTIC_WORKFLOW = (
    Status.DRAFT,
    Status.SUBMITTED,
    Status.MANAGER_APPROVAL,
    Status.MANAGER_APPROVED,
    Status.TRAVEL_BOOKING,
    Status.TRAVEL_BOOKED,
    Status.TRAVEL_IN_PROGRESS,
    Status.EXPENSE_SUBMISSION,
    Status.EXPENSE_VERIFICATION,
    Status.SETTLEMENT_PENDING,
    Status.SETTLEMENT_APPROVAL,
    Status.SETTLEMENT_APPROVED,
    Status.SETTLEMENT_PROCESSING,
    Status.COMPLETED,
    Status.CLOSED,
)

INTERNATIONAL_WORKFLOW = (
    Status.DRAFT,
    Status.SUBMITTED,
    Status.DOCUMENTS_PENDING,
    Status.DOCUMENTS_UNDER_REVIEW,
    Status.MANAGER_APPROVAL,
    Status.MANAGER_APPROVED,
    Status.VISA_PROCESSING,
    Status.VISA_APPROVED,
    Status.TRAVEL_BOOKING,
    Status.TRAVEL_BOOKED,
    Status.TRAVEL_IN_PROGRESS,
    Status.EXPENSE_SUBMISSION,
    Status.EXPENSE_VERIFICATION,
    Status.SETTLEMENT_PENDING,
    Status.SETTLEMENT_APPROVAL,
    Status.SETTLEMENT_APPROVED,
    Status.SETTLEMENT_PROCESSING,
    Status.COMPLETED,
    Status.CLOSED,
)

EXCEPTION_STATUSES = (
    Status.REQUEST_REJECTED,
    Status.REQUEST_CANCELLED,
)

WORKFLOW_DEFINITIONS = {
    TravelRequest.TravelType.DOMESTIC: DOMESTIC_WORKFLOW,
    TravelRequest.TravelType.INTERNATIONAL: INTERNATIONAL_WORKFLOW,
}


def workflow_for(travel_type):
    """
    Return the ordered status sequence for the given
    travel type, or None for legacy travel types
    (which have no new workflow).
    """

    return WORKFLOW_DEFINITIONS.get(travel_type)
