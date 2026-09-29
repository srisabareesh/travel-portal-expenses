from django.contrib import admin

from .models import FlightBooking, HotelBooking


@admin.register(FlightBooking)
class FlightBookingAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "airline",
        "flight_number",
        "booking_reference",
        "status",
        "departure_datetime",
    )

    list_filter = ("status", "airline")

    search_fields = (
        "travel_request__request_number",
        "booking_reference",
        "flight_number",
    )


@admin.register(HotelBooking)
class HotelBookingAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "hotel_name",
        "booking_reference",
        "status",
        "check_in",
        "check_out",
    )

    list_filter = ("status",)

    search_fields = (
        "travel_request__request_number",
        "booking_reference",
        "hotel_name",
    )
