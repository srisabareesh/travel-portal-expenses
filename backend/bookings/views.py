from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from travel.models import TravelRequest
from users.permissions import IsReviewerOrManager

from .models import FlightBooking, HotelBooking
from .serializers import (
    FlightBookingSerializer,
    HotelBookingSerializer,
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

        if not self._can_view(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

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

        if not self._can_view(
            request.user,
            travel_request,
        ):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

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
