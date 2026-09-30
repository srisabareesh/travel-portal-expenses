from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from travel.models import TravelRequest
from travel.services import Status as RequestStatus
from users.permissions import IsEmployee

from .models import Visa
from .serializers import VisaSerializer


def _get_international_request(travel_request_id):
    travel_request = get_object_or_404(
        TravelRequest,
        id=travel_request_id,
    )

    if (
        travel_request.travel_type
        != TravelRequest.TravelType.INTERNATIONAL
    ):
        return None

    return travel_request


def _get_or_create_visa(travel_request):
    visa, _created = Visa.objects.get_or_create(
        travel_request=travel_request,
        defaults={
            "country": travel_request.destination_country.name,
        },
    )

    return visa


def _request_in_visa_stage(travel_request):
    """
    The visa lifecycle may only be driven while the
    request is actually in (or past, for an approved
    visa being corrected) the visa processing stage.
    """

    return (
        travel_request.status
        == RequestStatus.VISA_PROCESSING
    )


def _can_view_visa(user, travel_request):
    if (
        travel_request.employee == user
        or user.has_role("REVIEWER")
        or user.has_role("MANAGER")
        or user.has_role("ADMIN")
    ):
        return True

    return False


class VisaDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):
        travel_request = _get_international_request(
            travel_request_id
        )

        if travel_request is None:
            return Response(
                {
                    "detail": (
                        "Visa tracking is only available "
                        "for international travel requests."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _can_view_visa(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        visa = _get_or_create_visa(travel_request)

        serializer = VisaSerializer(visa)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class VisaApplyView(APIView):

    """
    Employee-only: the employee records that they applied
    for the visa. Reviewer/HR and managers may view the
    visa but never update it.
    """

    permission_classes = [IsEmployee]

    def post(self, request, travel_request_id):
        travel_request = _get_international_request(
            travel_request_id
        )

        if travel_request is None:
            return Response(
                {
                    "detail": (
                        "Visa tracking is only available "
                        "for international travel requests."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ##Visa updates are gated on the workflow stage:
        ##documents verified, manager approved, visa
        ##processing started.
        if not _request_in_visa_stage(
            travel_request
        ):
            return Response(
                {
                    "detail": (
                        "Visa updates are only available "
                        "while the request is in visa "
                        "processing (after documents are "
                        "verified and the manager has "
                        "approved)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ##Only the travelling employee may update.
        if travel_request.employee != request.user:
            return Response(
                {
                    "detail": (
                        "Only the employee travelling can "
                        "update the visa status."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        visa = _get_or_create_visa(travel_request)

        if (
            visa.state
            not in (
                Visa.State.NOT_APPLIED,
                Visa.State.REJECTED,
            )
        ):
            return Response(
                {
                    "detail": (
                        "Visa can only be applied when "
                        "not applied or previously "
                        "rejected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        applied_on = request.data.get("applied_on")

        if not applied_on:
            return Response(
                {
                    "applied_on": (
                        "This field is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visa.state = Visa.State.APPLIED
        visa.applied_on = applied_on
        visa.remarks = request.data.get("remarks", "")
        visa.decided_by = None
        visa.decision_at = None

        visa.save()

        serializer = VisaSerializer(visa)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class VisaDecisionView(APIView):

    """
    Employee-only visa status updates (APPLIED /
    UNDER_PROCESS / APPROVED / REJECTED).

    On APPROVED the request automatically advances to the
    booking stage. On REJECTED the request stays in
    VISA_PROCESSING so the employee can re-apply.
    """

    permission_classes = [IsEmployee]

    def post(self, request, travel_request_id):
        travel_request = _get_international_request(
            travel_request_id
        )

        if travel_request is None:
            return Response(
                {
                    "detail": (
                        "Visa tracking is only available "
                        "for international travel requests."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ##Visa updates are gated on the workflow stage.
        if not _request_in_visa_stage(
            travel_request
        ):
            return Response(
                {
                    "detail": (
                        "Visa updates are only available "
                        "while the request is in visa "
                        "processing (after documents are "
                        "verified and the manager has "
                        "approved)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ##Only the travelling employee may update.
        if travel_request.employee != request.user:
            return Response(
                {
                    "detail": (
                        "Only the employee travelling can "
                        "update the visa status."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        visa = _get_or_create_visa(travel_request)

        if (
            visa.state
            not in (
                Visa.State.NOT_APPLIED,
                Visa.State.APPLIED,
                Visa.State.UNDER_PROCESS,
                Visa.State.REJECTED,
            )
        ):
            return Response(
                {
                    "detail": (
                        "Only a visa that is not yet "
                        "approved can be updated."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision = request.data.get("state")

        if decision not in (
            Visa.State.APPLIED,
            Visa.State.UNDER_PROCESS,
            Visa.State.APPROVED,
            Visa.State.REJECTED,
        ):
            return Response(
                {
                    "state": (
                        "State must be APPLIED, "
                        "UNDER_PROCESS, APPROVED or "
                        "REJECTED."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visa.state = decision
        visa.remarks = request.data.get(
            "remarks",
            visa.remarks,
        )

        if decision in (
            Visa.State.APPLIED,
        ):
            visa.applied_on = (
                request.data.get("applied_on")
                or timezone.now().date()
            )

        if decision in (
            Visa.State.APPROVED,
            Visa.State.REJECTED,
        ):
            visa.decided_by = request.user
            visa.decision_at = timezone.now()

        if decision == Visa.State.UNDER_PROCESS:
            visa.decided_by = None
            visa.decision_at = None

        visa.save()

        ##On APPROVED the request advances to the booking
        ##stage; on REJECTED it stays in VISA_PROCESSING.
        if decision == Visa.State.APPROVED:
            travel_request.status = (
                RequestStatus.VISA_APPROVED
            )

            travel_request.save(
                update_fields=["status", "updated_at"]
            )

            try:

                from audit.services import log_action

                log_action(
                    user=request.user,
                    action="VISA_APPROVED",
                    travel_request=travel_request,
                    previous_value=(
                        RequestStatus.VISA_PROCESSING
                    ),
                    new_value=(
                        RequestStatus.VISA_APPROVED
                    ),
                )

            except Exception:
                pass

            try:

                from notifications.services import (
                    notify_request_status_change,
                )

                notify_request_status_change(
                    travel_request,
                    event="REQUEST_VISA_APPROVED",
                    message=(
                        f"Travel request "
                        f"{travel_request.request_number}: "
                        f"visa approved; booking may start."
                    ),
                )

            except Exception:
                pass

        serializer = VisaSerializer(visa)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
