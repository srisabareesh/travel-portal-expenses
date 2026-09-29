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
    WorkflowError,
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


class ExpenseConfigurationView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
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

        if not (
            request.user.has_role("REVIEWER")
            or request.user.has_role("MANAGER")
        ):
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
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


class SettlementView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):
        travel_request = _get_travel_request(
            travel_request_id
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

        target, error = _workflow_transition(
            travel_request,
            "settle",
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
