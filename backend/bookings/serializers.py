from rest_framework import serializers

from .models import FlightBooking, HotelBooking


def _user_display_name(user):
    """Full name with username fallback."""

    if user is None:
        return ""

    full_name = (user.get_full_name() or "").strip()

    return full_name or user.get_username()


class FlightBookingSerializer(
    serializers.ModelSerializer
):

    recorded_by_name = serializers.SerializerMethodField()

    def get_recorded_by_name(self, obj):

        return _user_display_name(obj.recorded_by)

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
            "notes",
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

    recorded_by_name = serializers.SerializerMethodField()

    def get_recorded_by_name(self, obj):

        return _user_display_name(obj.recorded_by)

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
            "address",
            "room_details",
            "notes",
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
