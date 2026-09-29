from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from travel.models import TravelRequest
from users.permissions import IsReviewer, IsEmployee

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

    permission_classes = [IsReviewer]

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

    permission_classes = [IsReviewer]

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

        visa = _get_or_create_visa(travel_request)

        if (
            visa.state
            not in (
                Visa.State.APPLIED,
                Visa.State.UNDER_PROCESS,
            )
        ):
            return Response(
                {
                    "detail": (
                        "Only an applied or under-process "
                        "visa can receive a decision."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision = request.data.get("state")

        if decision not in (
            Visa.State.APPROVED,
            Visa.State.REJECTED,
            Visa.State.UNDER_PROCESS,
        ):
            return Response(
                {
                    "state": (
                        "State must be APPROVED, REJECTED "
                        "or UNDER_PROCESS."
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
            Visa.State.APPROVED,
            Visa.State.REJECTED,
        ):
            visa.decided_by = request.user
            visa.decision_at = timezone.now()

        if decision == Visa.State.UNDER_PROCESS:
            visa.decided_by = None
            visa.decision_at = None

        visa.save()

        serializer = VisaSerializer(visa)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
