from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from travel.models import TravelRequest
from travel.services import (
    ACTION_APPROVE_SETTLEMENT,
    ACTION_START_SETTLEMENT_APPROVAL,
    ACTION_START_SETTLEMENT_PROCESSING,
    Status,
    WorkflowError,
    get_effective_status,
    validate_transition,
)
from users.permissions import (
    IsEmployee,
    IsReviewer,
    IsReviewerOrManager,
)

from .models import Expense, ExpenseConfiguration, Settlement
from .serializers import (
    ExpenseConfigurationSerializer,
    ExpenseSerializer,
    SettlementSerializer,
)
from .services import calculate_settlement


def _get_travel_request(travel_request_id):
    return get_object_or_404(
        TravelRequest,
        id=travel_request_id,
    )


# Workflow stages in which expenses may be entered by the
# employee. TRAVEL_IN_PROGRESS is the trip itself
# (expenses may be recorded while travelling),
# EXPENSE_SUBMISSION is the dedicated expense-entry stage,
# and EXPENSE_VERIFICATION stays open for late receipts
# until the reviewer calculates the settlement (unverified
# expenses are simply excluded from it). Derived from the
# central workflow engine, never a second workflow
# definition.
_EXPENSE_ENTRY_STATUSES = (
    Status.TRAVEL_IN_PROGRESS,
    Status.EXPENSE_SUBMISSION,
    Status.EXPENSE_VERIFICATION,
)


# Workflow stages in which Reviewer/HR may configure the
# approved expense limits and the advance: after manager
# approval (or visa approval for international travel)
# and up to the end of the expense stages, so the limits
# exist before the settlement is calculated.
_EXPENSE_CONFIG_STATUSES = (
    Status.MANAGER_APPROVED,
    Status.VISA_APPROVED,
    Status.TRAVEL_BOOKING,
    Status.TRAVEL_BOOKED,
    Status.TRAVEL_IN_PROGRESS,
    Status.EXPENSE_SUBMISSION,
    Status.EXPENSE_VERIFICATION,
)


def _is_reviewer_or_manager(user):
    return user.has_role("REVIEWER") or user.has_role(
        "MANAGER"
    )


def _can_view_request(user, travel_request):
    """
    Object-level read visibility shared by the expense,
    configuration and settlement endpoints:

      EMPLOYEE  only their own request,
      REVIEWER/MANAGER  any request in the application
                (matches the existing reviewer scope in
                travel.views.TravelRequestViewSet, which
                grants reviewers the new workflow and
                managers their own + team requests),
      ADMIN     everything.
    """

    if travel_request.employee == user:
        return True

    if user.has_role("ADMIN"):
        return True

    return _is_reviewer_or_manager(user)


def _can_view_team_scope(user, travel_request):
    """
    Manager visibility follows the existing manager/team
    model: own requests plus direct team members' requests
    (travel.views.TravelRequestViewSet). Reviewers see the
    new workflow; admins see everything.
    """

    if travel_request.employee == user:
        return True

    if user.has_role("ADMIN"):
        return True

    if user.has_role("REVIEWER"):
        return True

    if user.has_role("MANAGER"):
        return travel_request.employee.manager == user

    return False


def _effective_status(travel_request):
    """
    Fold legacy statuses onto their new equivalents for
    stage guarding (interpretation only: the stored value
    is never rewritten). Legacy travel types keep their
    stored status, matching validate_transition.
    """

    from travel.services import is_legacy_travel_type

    if is_legacy_travel_type(
        travel_request.travel_type
    ):
        return travel_request.status

    return get_effective_status(travel_request)


class ExpenseConfigurationView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        ##Employees may read their own limits; reviewer
        ##and manager may read for any visible request.
        is_owner = (
            travel_request.employee == request.user
        )

        if not (
            is_owner
            or request.user.has_role("REVIEWER")
            or request.user.has_role("MANAGER")
            or request.user.has_role("ADMIN")
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        config = getattr(
            travel_request,
            "expense_configuration",
            None,
        )

        if config is None:
            return Response(
                {"detail": "Not configured yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ExpenseConfigurationSerializer(
            config
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        ##Limits (maximum approved expenses and the
        ##advance) are configured by REVIEWER/HR only.
        if not request.user.has_role("REVIEWER"):
            return Response(
                {
                    "detail": (
                        "Only Reviewer/HR can configure "
                        "expense limits and the advance."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        ##Stage guard (backend-authoritative): limits may
        ##only be configured after the request has been
        ##approved/visa-approved and before the settlement
        ##is calculated. Uses the workflow engine's status
        ##folding so legacy records behave consistently.
        if (
            _effective_status(travel_request)
            not in _EXPENSE_CONFIG_STATUSES
        ):
            return Response(
                {
                    "detail": (
                        "Expense limits can only be "
                        "configured after the request has "
                        "been approved and before the "
                        "settlement is calculated. Current "
                        f"status: {travel_request.status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        config = getattr(
            travel_request,
            "expense_configuration",
            None,
        )

        if config is None:
            serializer = ExpenseConfigurationSerializer(
                data=request.data
            )

            serializer.is_valid(raise_exception=True)

            serializer.save(
                travel_request=travel_request,
                configured_by=request.user,
            )
        else:
            serializer = ExpenseConfigurationSerializer(
                config,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(raise_exception=True)

            serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class ExpenseListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        if not _can_view_request(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        expenses = travel_request.expenses.all()

        serializer = ExpenseSerializer(
            expenses,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        if travel_request.employee != request.user:
            return Response(
                {
                    "detail": (
                        "You can only submit expenses for "
                        "your own travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        ##Stage guard (backend-authoritative): expenses may
        ##only be entered while the trip is in progress or
        ##during the expense submission / verification
        ##stages. The workflow engine's effective status
        ##keeps the guard consistent with the central
        ##workflow.
        if (
            _effective_status(travel_request)
            not in _EXPENSE_ENTRY_STATUSES
        ):
            return Response(
                {
                    "detail": (
                        "Expenses can only be submitted "
                        "while the trip is in progress "
                        "or during the expense stages. "
                        "Current status: "
                        f"{travel_request.status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ExpenseSerializer(
            data=request.data,
            context={
                "request": request,
                "travel_request": travel_request,
            },
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(
            travel_request=travel_request,
            submitted_by=request.user,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ExpenseVerifyView(APIView):

    permission_classes = [IsReviewer]

    def post(self, request, travel_request_id, expense_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        expense = get_object_or_404(
            Expense,
            id=expense_id,
            travel_request=travel_request,
        )

        if (
            expense.status
            != Expense.Status.SUBMITTED
        ):
            return Response(
                {
                    "detail": (
                        "Only submitted expenses can be "
                        "verified or rejected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision = request.data.get("status")

        if decision not in (
            Expense.Status.VERIFIED,
            Expense.Status.REJECTED,
        ):
            return Response(
                {
                    "status": (
                        "Status must be VERIFIED or REJECTED."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ##Self-verification is never allowed, regardless of
        ##additional roles: a user holding both EMPLOYEE and
        ##REVIEWER must not verify their own expense.
        if expense.submitted_by == request.user:
            return Response(
                {
                    "detail": (
                        "You cannot verify or reject your "
                        "own expense."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            decision == Expense.Status.REJECTED
            and not (
                request.data.get("review_comments", "")
                or ""
            ).strip()
        ):
            return Response(
                {
                    "review_comments": (
                        "Comments are required when "
                        "rejecting an expense."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = decision
        expense.reviewed_by = request.user
        expense.review_comments = request.data.get(
            "review_comments",
            "",
        )
        expense.reviewed_at = timezone.now()

        expense.save()

        serializer = ExpenseSerializer(expense)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


def _workflow_transition(
    travel_request,
    action_name,
    user,
):
    try:
        action, target = validate_transition(
            travel_request,
            action_name,
        )
    except WorkflowError as error:
        return None, error

    return target, None


def _settlement_calculated(travel_request):
    return getattr(
        travel_request,
        "settlement",
        None,
    ) is not None


class SettlementView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        ##Object-level visibility: the employee sees their
        ##own settlement, reviewers/managers follow the
        ##existing reviewer/manager scope, admin sees all.
        if not _can_view_team_scope(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        settlement = getattr(
            travel_request,
            "settlement",
            None,
        )

        if settlement is None:
            return Response(
                {"detail": "Not calculated yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SettlementSerializer(settlement)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SettlementCalculateView(APIView):

    permission_classes = [IsReviewer]

    def post(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
        )

        ##A settlement is calculated exactly once: if a
        ##record already exists the calculation is never
        ##repeated (refresh happens only through the
        ##explicit approval/processing steps).
        if getattr(
            travel_request,
            "settlement",
            None,
        ) is not None:
            settlement = travel_request.settlement

            return Response(
                {
                    "detail": (
                        "The settlement has already been "
                        "calculated."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        target, error = _workflow_transition(
            travel_request,
            "settle",
            request.user,
        )

        if error is not None:
            return Response(
                {
                    "detail": (
                        "Settlement can only be calculated "
                        "after expenses are verified (the "
                        "request must be in expense "
                        "verification). Current status: "
                        f"{travel_request.status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        travel_request.status = target

        travel_request.save(
            update_fields=["status", "updated_at"]
        )

        settlement = calculate_settlement(
            travel_request,
            request.user,
        )

        serializer = SettlementSerializer(settlement)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SettlementActionView(APIView):

    permission_classes = [IsAuthenticated]

    def post(
        self,
        request,
        travel_request_id,
        action,
    ):
        travel_request = _get_travel_request(
            travel_request_id
        )

        action_map = {
            "start-approval": (
                ACTION_START_SETTLEMENT_APPROVAL,
                Settlement,
            ),
            "approve": (ACTION_APPROVE_SETTLEMENT, None),
            "start-processing": (
                ACTION_START_SETTLEMENT_PROCESSING,
                None,
            ),
        }

        if action not in action_map:
            return Response(
                {"detail": "Unknown action."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action_name = action_map[action][0]

        ##A settlement must exist before any approval or
        ##processing step runs.
        if not _settlement_calculated(travel_request):
            return Response(
                {
                    "detail": (
                        "The settlement has not been "
                        "calculated yet."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ##Authorization mirrors the workflow engine's roles.
        if action_name == ACTION_APPROVE_SETTLEMENT:
            if not request.user.has_role("MANAGER"):
                return Response(
                    {"detail": "Permission denied."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if (
                travel_request.employee
                == request.user
            ):
                return Response(
                    {
                        "detail": (
                            "You cannot approve the "
                            "settlement of your own "
                            "travel request."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if (
                travel_request.employee.manager
                != request.user
                and not request.user.has_role("ADMIN")
            ):
                return Response(
                    {
                        "detail": (
                            "You can only approve "
                            "settlements of your own "
                            "team members."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        else:
            if not (
                request.user.has_role("REVIEWER")
                or request.user.has_role("MANAGER")
            ):
                return Response(
                    {"detail": "Permission denied."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        target, error = _workflow_transition(
            travel_request,
            action_name,
            request.user,
        )

        if error is not None:
            return Response(
                {"detail": error.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        travel_request.status = target

        travel_request.save(
            update_fields=["status", "updated_at"]
        )

        ##Keep the settlement record's own status in sync.
        settlement = getattr(
            travel_request,
            "settlement",
            None,
        )

        if settlement is not None:

            sync_map = {
                ACTION_START_SETTLEMENT_APPROVAL: (
                    Settlement.Status.IN_APPROVAL
                ),
                ACTION_APPROVE_SETTLEMENT: (
                    Settlement.Status.APPROVED
                ),
                ACTION_START_SETTLEMENT_PROCESSING: (
                    Settlement.Status.PROCESSING
                ),
            }

            if action_name in sync_map:

                settlement.status = sync_map[action_name]

                if (
                    action_name
                    == ACTION_APPROVE_SETTLEMENT
                ):
                    settlement.approved_by = (
                        request.user
                    )

                elif (
                    action_name
                    == ACTION_START_SETTLEMENT_PROCESSING
                ):
                    settlement.processed_by = (
                        request.user
                    )
                    settlement.payment_date = (
                        request.data.get("payment_date")
                        or settlement.payment_date
                    )
                    settlement.payment_reference = (
                        request.data.get(
                            "payment_reference",
                            settlement.payment_reference,
                        )
                    )
                    settlement.payment_method = (
                        request.data.get(
                            "payment_method",
                            settlement.payment_method,
                        )
                    )
                    settlement.remarks = request.data.get(
                        "remarks",
                        settlement.remarks,
                    )

                settlement.save()

        serializer = SettlementSerializer(
            travel_request.settlement
            if hasattr(travel_request, "settlement")
            else None
        ) if hasattr(travel_request, "settlement") else None

        if serializer is None:
            return Response(
                {"status": target},
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
