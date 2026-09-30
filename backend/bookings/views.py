from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from travel.models import TravelRequest
from travel.services import Status as RequestStatus
from users.permissions import IsReviewer

from .models import FlightBooking, HotelBooking
from .serializers import (
    FlightBookingSerializer,
    HotelBookingSerializer,
)


##Workflow stages in which bookings may be recorded.
##Domestic: after manager approval, until booking is
##completed. International: only after the visa is
##APPROVED (the request status then reads VISA_APPROVED
##or TRAVEL_BOOKING).
_DOMESTIC_BOOKING_STATUSES = (
    RequestStatus.MANAGER_APPROVED,
    RequestStatus.TRAVEL_BOOKING,
)

_INTERNATIONAL_BOOKING_STATUSES = (
    RequestStatus.VISA_APPROVED,
    RequestStatus.TRAVEL_BOOKING,
)


class _BookingBaseView(APIView):

    permission_classes = [IsAuthenticated]

    def _get_travel_request(self, travel_request_id):
        return get_object_or_404(
            TravelRequest,
            id=travel_request_id,
        )

    def _can_view(self, user, travel_request):
        return (
            travel_request.employee == user
            or user.has_role("REVIEWER")
            or user.has_role("MANAGER")
            or user.has_role("ADMIN")
        )

    def _can_record(self, user, travel_request):
        """
        Booking records are created and edited by
        REVIEWER/HR only, and only while the request is in
        the booking window (after approval/visa approval,
        before booking completion).

        Returns (allowed, error_response).
        """

        if not user.has_role("REVIEWER"):
            return False, (
                Response(
                    {
                        "detail": (
                            "Only Reviewer/HR can record "
                            "bookings."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            )

        if travel_request.travel_type == (
            TravelRequest.TravelType.INTERNATIONAL
        ):
            window = _INTERNATIONAL_BOOKING_STATUSES
        else:
            window = _DOMESTIC_BOOKING_STATUSES

        if travel_request.status not in window:
            return False, (
                Response(
                    {
                        "detail": (
                            "Bookings can only be recorded "
                            "after the request has been "
                            "approved"
                            + (
                                " and the visa is approved"
                                if travel_request.travel_type
                                == (
                                    TravelRequest.TravelType.INTERNATIONAL
                                )
                                else ""
                            )
                            + ", while the request is in "
                            "the booking stage."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            )

        return True, None


class FlightBookingListCreateView(
    _BookingBaseView
):

    def get(self, request, travel_request_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        if not self._can_view(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        bookings = FlightBooking.objects.filter(
            travel_request=travel_request
        ).order_by("id")

        serializer = FlightBookingSerializer(
            bookings,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, travel_request_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        allowed, error_response = self._can_record(
            request.user,
            travel_request,
        )

        if not allowed:
            return error_response

        serializer = FlightBookingSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(
            travel_request=travel_request,
            recorded_by=request.user,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class FlightBookingDetailView(
    _BookingBaseView
):

    def _get_booking(self, booking_id):
        return get_object_or_404(
            FlightBooking,
            id=booking_id,
        )

    def get(self, request, travel_request_id, booking_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        if not self._can_view(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        booking = self._get_booking(booking_id)

        serializer = FlightBookingSerializer(booking)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, travel_request_id, booking_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        allowed, error_response = self._can_record(
            request.user,
            travel_request,
        )

        if not allowed:
            return error_response

        booking = self._get_booking(booking_id)

        serializer = FlightBookingSerializer(
            booking,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class HotelBookingListCreateView(
    _BookingBaseView
):

    def get(self, request, travel_request_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        if not self._can_view(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        bookings = HotelBooking.objects.filter(
            travel_request=travel_request
        ).order_by("id")

        serializer = HotelBookingSerializer(
            bookings,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, travel_request_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        allowed, error_response = self._can_record(
            request.user,
            travel_request,
        )

        if not allowed:
            return error_response

        serializer = HotelBookingSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(
            travel_request=travel_request,
            recorded_by=request.user,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class HotelBookingDetailView(
    _BookingBaseView
):

    def _get_booking(self, booking_id):
        return get_object_or_404(
            HotelBooking,
            id=booking_id,
        )

    def get(self, request, travel_request_id, booking_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        if not self._can_view(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        booking = self._get_booking(booking_id)

        serializer = HotelBookingSerializer(booking)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, travel_request_id, booking_id):
        travel_request = self._get_travel_request(
            travel_request_id
        )

        allowed, error_response = self._can_record(
            request.user,
            travel_request,
        )

        if not allowed:
            return error_response

        booking = self._get_booking(booking_id)

        serializer = HotelBookingSerializer(
            booking,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
