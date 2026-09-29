from django.shortcuts import get_object_or_404
from django.shortcuts import get_object_or_404 as _get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.services import (
    are_all_mandatory_documents_verified,
    get_required_documents,
)

from .models import Country, TravelRequest

from .services import Status
from .models import TravelRequest as _TR  # noqa: F401

from .serializers import (
    CountrySerializer,
    TravelRequestSerializer,
)
from .services import (
    WorkflowError,
    ACTION_APPROVE,
    ACTION_APPROVE_SETTLEMENT,
    ACTION_CANCEL,
    ACTION_CLOSE,
    ACTION_COMPLETE,
    ACTION_COMPLETE_BOOKING,
    ACTION_REJECT,
    ACTION_SETTLE,
    ACTION_START_BOOKING,
    ACTION_START_EXPENSE_REVIEW,
    ACTION_START_REVIEW,
    ACTION_START_SETTLEMENT_APPROVAL,
    ACTION_START_SETTLEMENT_PROCESSING,
    ACTION_START_TRAVEL,
    ACTION_START_VISA,
    ACTION_SUBMIT,
    ACTION_SUBMIT_EXPENSES,
    ACTION_SUBMIT_FOR_APPROVAL,
    ACTION_VISA_DECIDE,
    get_allowed_actions,
    get_workflow_progress,
)


# ----------------------------------------------------------
# Phase 3.6/3.7: central workflow engine & transition API
# ----------------------------------------------------------

import django.db.transaction as _transaction

from rest_framework.exceptions import (
    PermissionDenied as _PermissionDenied,
    ValidationError as _ValidationError,
)

from documents.services import (
    are_all_mandatory_documents_verified as _all_docs_verified,
)

from .services import (
    WorkflowError,
    ACTION_APPROVE,
    ACTION_APPROVE_SETTLEMENT,
    ACTION_CANCEL,
    ACTION_COMPLETE,
    ACTION_COMPLETE_BOOKING,
    ACTION_REJECT,
    ACTION_START_BOOKING,
    ACTION_START_EXPENSE_REVIEW,
    ACTION_START_REVIEW,
    ACTION_START_SETTLEMENT_APPROVAL,
    ACTION_START_SETTLEMENT_PROCESSING,
    ACTION_START_TRAVEL,
    ACTION_START_VISA,
    ACTION_SUBMIT,
    ACTION_SUBMIT_EXPENSES,
    ACTION_SUBMIT_FOR_APPROVAL,
    ACTION_SETTLE,
    ACTION_VISA_DECIDE,
    get_allowed_actions,
    get_current_stage,
    get_next_stage,
    get_previous_stage,
    get_workflow,
    get_workflow_progress,
    is_exception_status,
    is_legacy_travel_type,
    validate_transition,
)

# Role requirements per action. USER means: any authenticated
# user; ownership/assignment checks are applied separately.
_ACTION_ROLES = {
    ACTION_SUBMIT: ("EMPLOYEE",),
    ACTION_START_REVIEW: ("REVIEWER",),
    ACTION_SUBMIT_FOR_APPROVAL: ("REVIEWER",),
    ACTION_APPROVE: ("MANAGER",),
    ACTION_REJECT: ("MANAGER",),
    ACTION_CANCEL: ("EMPLOYEE", "MANAGER", "ADMIN"),
    ACTION_START_VISA: ("REVIEWER",),
    ACTION_VISA_DECIDE: ("REVIEWER",),
    ACTION_START_BOOKING: ("REVIEWER",),
    ACTION_COMPLETE_BOOKING: ("REVIEWER",),
    ACTION_START_TRAVEL: ("EMPLOYEE", "REVIEWER"),
    ACTION_SUBMIT_EXPENSES: ("EMPLOYEE",),
    ACTION_START_EXPENSE_REVIEW: ("REVIEWER",),
    ACTION_SETTLE: ("REVIEWER",),
    ACTION_START_SETTLEMENT_APPROVAL: ("REVIEWER",),
    ACTION_APPROVE_SETTLEMENT: ("MANAGER",),
    ACTION_START_SETTLEMENT_PROCESSING: ("REVIEWER",),
    ACTION_COMPLETE: ("REVIEWER",),
    ACTION_CLOSE: ("ADMIN", "EMPLOYEE", "MANAGER"),
}


def _user_has_any_role(user, roles):
    return any(user.has_role(role) for role in roles)


def _is_reviewer_or_manager(user):
    return _user_has_any_role(
        user, ("REVIEWER", "MANAGER")
    )


def _check_action_authorization(
    travel_request,
    action,
    user,
):
    """
    Backend authorization for a workflow action.

    Raises PermissionDenied when the user may not perform
    the action on this request.
    """

    roles = _ACTION_ROLES.get(action, ())

    if roles and not _user_has_any_role(user, roles):
        raise _PermissionDenied(
            "You do not have permission to perform "
            "this workflow action."
        )

    is_owner = travel_request.employee == user

    if action == ACTION_SUBMIT:
        if not is_owner:
            raise _PermissionDenied(
                "You can only submit your own "
                "travel request."
            )

    elif action == ACTION_SUBMIT_EXPENSES:
        if not is_owner:
            raise _PermissionDenied(
                "You can only submit expenses for "
                "your own travel request."
            )

    elif action in (ACTION_APPROVE, ACTION_REJECT):
        if is_owner:
            raise _PermissionDenied(
                "You cannot approve or reject your "
                "own travel request."
            )

        if (
            travel_request.employee.manager != user
            and not user.has_role("ADMIN")
        ):
            ##Explicitly assigned MANAGERs approve only
            ##their own team's requests. An ADMIN acting
            ##with an explicit MANAGER role is a business
            ##fallback, still never for own requests.
            raise _PermissionDenied(
                "You can only approve or reject "
                "requests of your own team "
                "members."
            )

    elif action == ACTION_CANCEL:
        if (
            not is_owner
            and not _user_has_any_role(
                user, ("MANAGER", "ADMIN")
            )
        ):
            raise _PermissionDenied(
                "You do not have permission to "
                "cancel this travel request."
            )

    elif action in (
        ACTION_START_VISA,
        ACTION_VISA_DECIDE,
        ACTION_START_BOOKING,
        ACTION_COMPLETE_BOOKING,
        ACTION_SETTLE,
        ACTION_START_EXPENSE_REVIEW,
        ACTION_START_SETTLEMENT_APPROVAL,
        ACTION_APPROVE_SETTLEMENT,
        ACTION_START_SETTLEMENT_PROCESSING,
        ACTION_COMPLETE,
    ):
        ##Reviewer/manager operations act on any request
        ##that has entered the new workflow.
        if is_owner and not user.has_role("ADMIN"):
            ##Self-review/self-approval is never allowed.
            raise _PermissionDenied(
                "You cannot perform this action on "
                "your own travel request."
            )

    elif action in (
        ACTION_START_REVIEW,
        ACTION_SUBMIT_FOR_APPROVAL,
        ACTION_START_SETTLEMENT_PROCESSING,
    ):
        pass


def _apply_workflow_transition(
    travel_request,
    action_name,
    user,
    extra_requirements=None,
):
    """
    Shared transition helper: authorizes, validates and
    applies the status change inside a transaction.

    Returns the target status.
    """

    ##Authorization is evaluated before transition
    ##validation: an unauthorized caller gets 403 even
    ##when the transition would also be invalid, and is
    ##not told anything about the request's state.
    action, target = validate_transition(
        travel_request,
        action_name,
        _authorize=False,
    )

    _check_action_authorization(
        travel_request,
        action,
        user,
    )

    if target is None:

        ##Full validation raises the precise error for an
        ##action unavailable at the current status.
        validate_transition(
            travel_request,
            action_name,
        )

    else:

        ##Authorization has passed: re-run full validation
        ##(workflow membership, stage adjacency and the
        ##travel-type guards) before mutating anything.
        _action, target = validate_transition(
            travel_request,
            action_name,
        )

    if extra_requirements:

        for requirement in extra_requirements:

            ##Prerequisite callables receive the request
            ##they are evaluated against.
            if not requirement(travel_request):
                raise _ValidationError(
                    {
                        "detail": (
                            "Business prerequisites "
                            "for this action are "
                            "not met."
                        )
                    }
                )

    previous_status = travel_request.status

    with _transaction.atomic():

        travel_request.status = target

        travel_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    ##Centralized side effects (audit + notification)
    ##must never break the transition itself.
    try:

        from audit.services import log_action

        log_action(
            user=user,
            action=action_name.upper(),
            travel_request=travel_request,
            previous_value=previous_status,
            new_value=target,
        )

    except Exception:
        pass

    try:

        from notifications.services import (
            notify_request_status_change,
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

    except Exception:
        pass

    return target


def _transition_response(
    self,
    request,
    action_name,
    extra_requirements=None,
):
    """
    Shared endpoint body for all POST workflow actions.
    """

    travel_request = _get_object_or_404(
        TravelRequest,
        pk=self.kwargs.get("pk"),
    )

    try:

        _apply_workflow_transition(
            travel_request,
            action_name,
            request.user,
            extra_requirements=extra_requirements,
        )

    except WorkflowError as error:

        return Response(
            {"detail": error.message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = self.get_serializer(
        travel_request
    )

    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )


class WorkflowActionViewSetMixin:
    """
    Adds the workflow action endpoints to a ViewSet.
    """

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(self, request, pk=None):
        ##Historical requests carrying a legacy travel
        ##type keep their original submit behavior: the
        ##document checklist decides between
        ##DOCUMENT_PENDING and DOCUMENT_VERIFICATION.
        ##(DRAFT/SUBMITTED are shared by legacy and new
        ##workflows, so the travel type is the reliable
        ##discriminator - not the status.)
        from .services import is_legacy_travel_type

        travel_request = _get_object_or_404(
            TravelRequest,
            pk=pk,
        )

        if is_legacy_travel_type(travel_request.travel_type):
            return self._legacy_submit(
                request,
                travel_request,
            )

        return _transition_response(
            self,
            request,
            ACTION_SUBMIT,
        )

    def _legacy_submit(self, request, travel_request):
        if travel_request.employee != request.user:
            return Response(
                {"detail": "You do not have permission to submit this travel request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        requirements = get_required_documents(travel_request)

        mandatory = [r for r in requirements if r.mandatory]

        latest = {}

        for document in travel_request.documents.all().order_by(
            "-uploaded_at", "-id"
        ):
            if document.document_type_id not in latest:
                latest[document.document_type_id] = document

        missing = [r for r in mandatory if r.document_type_id not in latest]

        travel_request.status = (
            TravelRequest.Status.DOCUMENT_PENDING
            if missing
            else TravelRequest.Status.DOCUMENT_VERIFICATION
        )

        travel_request.save(update_fields=["status", "updated_at"])

        from audit.services import log_action

        log_action(
            user=request.user,
            action="SUBMIT",
            travel_request=travel_request,
            previous_value="DRAFT",
            new_value=travel_request.status,
        )

        serializer = self.get_serializer(travel_request)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="start-review",
    )
    def start_review(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_REVIEW,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit-for-approval",
    )
    def submit_for_approval(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_SUBMIT_FOR_APPROVAL,
            extra_requirements=[
                _all_docs_verified,
            ],
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_APPROVE,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
        url_name="workflow-reject",
    )
    def reject(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_REJECT,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_CANCEL,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-visa",
    )
    def start_visa(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_VISA,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="visa-decide",
    )
    def visa_decide(self, request, pk=None):
        decision = (
            request.data.get("decision", "")
            if isinstance(request.data, dict)
            else ""
        )

        if decision not in ("APPROVED", "REJECTED"):
            return Response(
                {
                    "decision": (
                        "Decision must be APPROVED "
                        "or REJECTED."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if decision == "REJECTED":
            return Response(
                {
                    "detail": (
                        "Visa rejection handling is "
                        "part of the visa module."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return _transition_response(
            self,
            request,
            ACTION_VISA_DECIDE,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-booking",
    )
    def start_booking(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_BOOKING,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete-booking",
    )
    def complete_booking(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_COMPLETE_BOOKING,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-travel",
    )
    def start_travel(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_TRAVEL,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit-expenses",
    )
    def submit_expenses(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_SUBMIT_EXPENSES,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-expense-review",
    )
    def start_expense_review(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_EXPENSE_REVIEW,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="settle",
    )
    def settle(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_SETTLE,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-settlement-approval",
    )
    def start_settlement_approval(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_SETTLEMENT_APPROVAL,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve-settlement",
    )
    def approve_settlement(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_APPROVE_SETTLEMENT,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-settlement-processing",
    )
    def start_settlement_processing(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_START_SETTLEMENT_PROCESSING,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_COMPLETE,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="close",
    )
    def close(self, request, pk=None):
        return _transition_response(
            self,
            request,
            ACTION_CLOSE,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="workflow",
    )
    def workflow(self, request, pk=None):
        travel_request = _get_object_or_404(
            TravelRequest,
            pk=pk,
        )

        progress = get_workflow_progress(
            travel_request
        )

        progress["allowed_actions"] = (
            get_allowed_actions(travel_request)
        )

        return Response(
            progress,
            status=status.HTTP_200_OK,
        )


class CountryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]


class TravelRequestViewSet(
    WorkflowActionViewSetMixin,
    viewsets.ModelViewSet,
):

    serializer_class = TravelRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        if user.has_role("ADMIN"):
            return TravelRequest.objects.all()

        if user.has_role("REVIEWER"):

            ##Phase 3.7: reviewers see their own requests,
            ##legacy document-workflow requests and every
            ##request travelling the new workflow (the
            ##engine drives those through review stages).
            legacy_workflow_requests = (
                TravelRequest.objects.filter(
                    status__in=[
                        TravelRequest.Status.DOCUMENT_PENDING,
                        TravelRequest.Status.DOCUMENT_VERIFICATION,
                    ]
                )
            )

            new_workflow_requests = (
                TravelRequest.objects.filter(
                    travel_type__in=[
                        TravelRequest.TravelType.DOMESTIC,
                        TravelRequest.TravelType.INTERNATIONAL,
                    ],
                    status__in=[
                        Status.SUBMITTED,
                        Status.DOCUMENTS_PENDING,
                        Status.DOCUMENTS_UNDER_REVIEW,
                        Status.MANAGER_APPROVAL,
                        Status.MANAGER_APPROVED,
                        Status.TRAVEL_BOOKING,
                        Status.TRAVEL_BOOKED,
                        Status.VISA_PROCESSING,
                        Status.VISA_APPROVED,
                        Status.EXPENSE_SUBMISSION,
                        Status.EXPENSE_VERIFICATION,
                        Status.SETTLEMENT_PENDING,
                        Status.SETTLEMENT_APPROVAL,
                        Status.SETTLEMENT_APPROVED,
                        Status.SETTLEMENT_PROCESSING,
                    ],
                )
            )

            own_requests = TravelRequest.objects.filter(
                employee=user
            )

            return (
                legacy_workflow_requests
                | new_workflow_requests
                | own_requests
            ).distinct()

        if user.has_role("MANAGER"):

            own_requests = TravelRequest.objects.filter(
                employee=user
            )

            team_requests = TravelRequest.objects.filter(
                employee__manager=user
            )

            return (
                own_requests
                | team_requests
            ).distinct()

        return TravelRequest.objects.filter(
            employee=user
        )

    def perform_create(self, serializer):

        serializer.save(
            employee=self.request.user
        )

    def perform_update(self, serializer):

        travel_request = self.get_object()

        if (
            travel_request.employee
            != self.request.user
        ):
            from rest_framework.exceptions import (
                PermissionDenied,
            )

            raise PermissionDenied(
                "You do not have permission "
                "to modify this travel request."
            )

        if (
            travel_request.status
            != TravelRequest.Status.DRAFT
        ):
            from rest_framework.exceptions import (
                ValidationError,
            )

            raise ValidationError(
                {
                    "detail": (
                        "Only draft travel requests "
                        "can be modified."
                    )
                }
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):

        travel_request = self.get_object()

        if (
            travel_request.employee
            != request.user
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to delete this travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            travel_request.status
            != TravelRequest.Status.DRAFT
        ):
            return Response(
                {
                    "detail": (
                        "Only draft travel requests "
                        "can be deleted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )

    ##The legacy hand-written submit/approve/reject
    ##implementations were replaced by the central
    ##workflow engine (Phase 3.7). The same endpoints
    ##now delegate to the engine, which validates the
    ##transition, the role, ownership and prerequisites.
