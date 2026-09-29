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

from django.db import transaction

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


# ==========================================================
# Central workflow engine (Phase 3.6)
#
# The workflow engine is the single authority for status
# transitions. Views and serializers must never hard-code
# transition rules; they call the functions below.
# ==========================================================

from .models import TravelRequest as _TR


class WorkflowError(Exception):
    """Raised when a workflow rule is violated."""

    def __init__(self, message, code="invalid_transition"):
        super().__init__(message)
        self.message = message
        self.code = code


# Actions that any authenticated user may attempt; all other
# permissions are resolved from the action + request state.
ACTION_SUBMIT = "submit"
ACTION_START_REVIEW = "start_review"
ACTION_SUBMIT_FOR_APPROVAL = "submit_for_approval"
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_CANCEL = "cancel"
ACTION_START_VISA = "start_visa"
ACTION_VISA_DECIDE = "visa_decide"
ACTION_START_BOOKING = "start_booking"
ACTION_COMPLETE_BOOKING = "complete_booking"
ACTION_START_TRAVEL = "start_travel"
ACTION_SUBMIT_EXPENSES = "submit_expenses"
ACTION_START_EXPENSE_REVIEW = "start_expense_review"
ACTION_SETTLE = "settle"
ACTION_START_SETTLEMENT_APPROVAL = "start_settlement_approval"
ACTION_APPROVE_SETTLEMENT = "approve_settlement"
ACTION_START_SETTLEMENT_PROCESSING = "start_settlement_processing"
ACTION_COMPLETE = "complete"
ACTION_CLOSE = "close"

_ACTION_BY_NAME = {
    "submit": ACTION_SUBMIT,
    "start_review": ACTION_START_REVIEW,
    "submit_for_approval": ACTION_SUBMIT_FOR_APPROVAL,
    "approve": ACTION_APPROVE,
    "reject": ACTION_REJECT,
    "cancel": ACTION_CANCEL,
    "start_visa": ACTION_START_VISA,
    "visa_decide": ACTION_VISA_DECIDE,
    "start_booking": ACTION_START_BOOKING,
    "complete_booking": ACTION_COMPLETE_BOOKING,
    "start_travel": ACTION_START_TRAVEL,
    "submit_expenses": ACTION_SUBMIT_EXPENSES,
    "start_expense_review": ACTION_START_EXPENSE_REVIEW,
    "settle": ACTION_SETTLE,
    "start_settlement_approval": ACTION_START_SETTLEMENT_APPROVAL,
    "approve_settlement": ACTION_APPROVE_SETTLEMENT,
    "start_settlement_processing": ACTION_START_SETTLEMENT_PROCESSING,
    "complete": ACTION_COMPLETE,
    "close": ACTION_CLOSE,
}

# action -> {status: target_status}
TRANSITION_MAP = {
    ACTION_SUBMIT: {
        Status.DRAFT: Status.SUBMITTED,
    },
    ACTION_START_REVIEW: {
        Status.SUBMITTED: Status.DOCUMENTS_PENDING,
    },
    ACTION_SUBMIT_FOR_APPROVAL: {
        Status.SUBMITTED: Status.MANAGER_APPROVAL,
        Status.DOCUMENTS_PENDING: Status.MANAGER_APPROVAL,
        Status.DOCUMENTS_UNDER_REVIEW: Status.MANAGER_APPROVAL,
        Status.DOCUMENT_PENDING: Status.MANAGER_APPROVAL,
        Status.DOCUMENT_VERIFICATION: Status.MANAGER_APPROVAL,
    },
    ACTION_APPROVE: {
        Status.MANAGER_APPROVAL: Status.MANAGER_APPROVED,
    },
    ACTION_REJECT: {
        Status.MANAGER_APPROVAL: Status.REQUEST_REJECTED,
    },
    ACTION_CANCEL: {
        Status.DRAFT: Status.REQUEST_CANCELLED,
        Status.SUBMITTED: Status.REQUEST_CANCELLED,
        Status.DOCUMENTS_PENDING: Status.REQUEST_CANCELLED,
        Status.DOCUMENTS_UNDER_REVIEW: Status.REQUEST_CANCELLED,
        Status.MANAGER_APPROVAL: Status.REQUEST_CANCELLED,
    },
    ACTION_START_VISA: {
        Status.MANAGER_APPROVED: Status.VISA_PROCESSING,
    },
    ACTION_VISA_DECIDE: {
        Status.VISA_PROCESSING: Status.VISA_APPROVED,
    },
    ACTION_START_BOOKING: {
        Status.MANAGER_APPROVED: Status.TRAVEL_BOOKING,
        Status.VISA_APPROVED: Status.TRAVEL_BOOKING,
    },
    ACTION_COMPLETE_BOOKING: {
        Status.TRAVEL_BOOKING: Status.TRAVEL_BOOKED,
    },
    ACTION_START_TRAVEL: {
        Status.TRAVEL_BOOKED: Status.TRAVEL_IN_PROGRESS,
    },
    ACTION_SUBMIT_EXPENSES: {
        Status.TRAVEL_IN_PROGRESS: Status.EXPENSE_SUBMISSION,
    },
    ACTION_START_EXPENSE_REVIEW: {
        Status.EXPENSE_SUBMISSION: Status.EXPENSE_VERIFICATION,
    },
    ACTION_SETTLE: {
        Status.EXPENSE_VERIFICATION: Status.SETTLEMENT_PENDING,
    },
    ACTION_START_SETTLEMENT_APPROVAL: {
        Status.SETTLEMENT_PENDING: Status.SETTLEMENT_APPROVAL,
    },
    ACTION_APPROVE_SETTLEMENT: {
        Status.SETTLEMENT_APPROVAL: Status.SETTLEMENT_APPROVED,
    },
    ACTION_START_SETTLEMENT_PROCESSING: {
        Status.SETTLEMENT_APPROVED: Status.SETTLEMENT_PROCESSING,
    },
    ACTION_COMPLETE: {
        Status.SETTLEMENT_PROCESSING: Status.COMPLETED,
    },
    ACTION_CLOSE: {
        Status.COMPLETED: Status.CLOSED,
    },
}

# Actions whose target is a terminal exception outcome.
EXCEPTION_ACTIONS = frozenset(
    {
        ACTION_REJECT,
        ACTION_CANCEL,
    }
)


def get_workflow(travel_request):
    """Return the ordered workflow tuple for the request."""

    workflow = workflow_for(travel_request.travel_type)

    if workflow is None:
        raise WorkflowError(
            "This travel request uses a historical travel "
            "type without a new workflow.",
            code="no_workflow",
        )

    return workflow


def validate_transition(
    travel_request,
    action_name,
    _authorize=True,
):
    """
    Validate that the action can be applied to the request.

    Returns (action, target_status). Raises WorkflowError
    when the action is unknown or not valid for the
    request's current status.

    With _authorize=False the user-independent guards are
    skipped: the view applies HTTP authorization first and
    then re-runs full validation (an unauthorized caller
    gets 403 without learning the request's state).
    """

    action = _ACTION_BY_NAME.get(action_name)

    if action is None:
        raise WorkflowError(
            f"Unknown workflow action '{action_name}'.",
            code="unknown_action",
        )

    if not _authorize:

        mapping = TRANSITION_MAP.get(action, {})

        return action, mapping.get(
            travel_request.status
        )

    workflow = get_workflow(travel_request)

    if travel_request.status not in workflow:
        raise WorkflowError(
            "This request uses a historical status and "
            "cannot be moved through the new workflow.",
            code="legacy_status",
        )

    mapping = TRANSITION_MAP.get(action, {})

    target = mapping.get(travel_request.status)

    if target is None:
        raise WorkflowError(
            f"Action '{action_name}' is not available "
            f"while the request is "
            f"{travel_request.status}.",
            code="invalid_transition",
        )

    ##Exception outcomes may target statuses outside the
    ##happy path. For happy-path targets the target must
    ##appear directly after the current status in the
    ##request's workflow, when the target is itself part
    ##of that workflow. Some transitions legitimately
    ##target a status the other workflow does not contain
    ##(e.g. the shared SUBMITTED branch into the
    ##international-only document stages), and the
    ##approval hand-off is additionally gated by the
    ##mandatory-documents prerequisite instead of pure
    ##stage adjacency.
    if (
        action not in EXCEPTION_ACTIONS
        and action != ACTION_SUBMIT_FOR_APPROVAL
        and target in workflow
        and workflow.index(travel_request.status) + 1
        != workflow.index(target)
    ):
        raise WorkflowError(
            f"Action '{action_name}' would skip workflow "
            "stages.",
            code="stage_skip",
        )

    ##Travel-type guards: the document review and visa
    ##stages exist only for international travel, and a
    ##domestic request goes straight from SUBMITTED to
    ##manager approval.
    if (
        action
        in (
            ACTION_START_REVIEW,
            ACTION_START_VISA,
            ACTION_VISA_DECIDE,
        )
        and travel_request.travel_type
        != TravelRequest.TravelType.INTERNATIONAL
    ):
        raise WorkflowError(
            "This action only applies to "
            "international travel requests.",
            code="invalid_transition",
        )

    if (
        action == ACTION_SUBMIT_FOR_APPROVAL
        and travel_request.status == Status.SUBMITTED
        and travel_request.travel_type
        != TravelRequest.TravelType.DOMESTIC
    ):
        raise WorkflowError(
            "International requests must pass the "
            "document stages before manager "
            "approval.",
            code="invalid_transition",
        )

    return action, target


def get_current_stage(travel_request):
    """Return the request's current workflow stage."""

    workflow = get_workflow(travel_request)

    if travel_request.status not in workflow:
        return None

    return travel_request.status


def get_next_stage(travel_request):
    """Return the next happy-path stage, or None at the end."""

    workflow = get_workflow(travel_request)

    if travel_request.status not in workflow:
        return None

    index = workflow.index(travel_request.status)

    if index + 1 >= len(workflow):
        return None

    return workflow[index + 1]


def get_previous_stage(travel_request):
    """Return the previous happy-path stage, or None at start."""

    workflow = get_workflow(travel_request)

    if travel_request.status not in workflow:
        return None

    index = workflow.index(travel_request.status)

    if index == 0:
        return None

    return workflow[index - 1]


def get_allowed_actions(travel_request, user=None):
    """
    Return the list of action names whose status
    transition is currently valid for the request.
    """

    allowed = []

    for action_name in _ACTION_BY_NAME:

        try:
            validate_transition(
                travel_request,
                action_name,
            )
        except WorkflowError:
            continue

        allowed.append(action_name)

    return allowed


def get_workflow_progress(travel_request):
    """
    Return the workflow definition, the current position
    and the completed / pending stages for the request.
    """

    workflow = get_workflow(travel_request)

    status = travel_request.status

    if status not in workflow:
        return {
            "travel_type": travel_request.travel_type,
            "workflow": list(workflow),
            "current_stage": None,
            "completed_stages": [],
            "pending_stage": None,
            "is_exception": True,
        }

    index = workflow.index(status)

    return {
        "travel_type": travel_request.travel_type,
        "workflow": list(workflow),
        "current_stage": status,
        "completed_stages": list(workflow[: index + 1]),
        "pending_stage": get_next_stage(travel_request),
        "is_exception": is_exception_status(status),
    }


def apply_workflow_transition_with_side_effects(
    travel_request,
    action_name,
    user,
    comment="",
):
    """
    Apply a validated workflow transition and record the
    centralized side effects: an audit entry and, where
    meaningful, an in-app notification for the employee.

    Returns the target status. Raises WorkflowError for
    invalid/unauthorized transitions (audit/notification
    failures never block the transition).
    """

    from audit.services import log_action
    from notifications.services import (
        notify_request_status_change,
    )

    ##Authorization is enforced by the view layer via
    ##_check_action_authorization; here we validate the
    ##transition itself.
    action, target = validate_transition(
        travel_request,
        action_name,
    )

    previous_status = travel_request.status

    with transaction.atomic():

        travel_request.status = target

        travel_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    log_action(
        user=user,
        action=action_name.upper(),
        travel_request=travel_request,
        previous_value=previous_status,
        new_value=target,
        comment=comment,
    )

    notify_request_status_change(
        travel_request,
        event=f"REQUEST_{action_name.upper()}",
        message=(
            f"Travel request "
            f"{travel_request.request_number}: "
            f"{previous_status} -> {target}."
        ),
    )

    return target
