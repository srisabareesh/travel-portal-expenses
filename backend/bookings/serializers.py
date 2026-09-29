from rest_framework import serializers

from .models import FlightBooking, HotelBooking


class FlightBookingSerializer(
    serializers.ModelSerializer
):

    recorded_by_name = serializers.CharField(
        source="recorded_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = FlightBooking

        fields = (
            "id",
            "travel_request",
            "status",
            "airline",
            "flight_number",
            "booking_reference",
            "departure_datetime",
            "arrival_datetime",
            "origin",
            "destination",
            "cost",
            "currency",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "recorded_by",
            "created_at",
            "updated_at",
        )


class HotelBookingSerializer(
    serializers.ModelSerializer
):

    recorded_by_name = serializers.CharField(
        source="recorded_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = HotelBooking

        fields = (
            "id",
            "travel_request",
            "status",
            "hotel_name",
            "booking_reference",
            "check_in",
            "check_out",
            "location",
            "room_details",
            "cost",
            "currency",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "recorded_by",
            "created_at",
            "updated_at",
        )
