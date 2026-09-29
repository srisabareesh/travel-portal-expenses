from django.urls import path

from .views import (
    FlightBookingDetailView,
    FlightBookingListCreateView,
    HotelBookingDetailView,
    HotelBookingListCreateView,
)


urlpatterns = [
    path(
        "travel-requests/<int:travel_request_id>/bookings/flights/",
        FlightBookingListCreateView.as_view(),
        name="flight-bookings",
    ),
    path(
        "travel-requests/<int:travel_request_id>/bookings/flights/<int:booking_id>/",
        FlightBookingDetailView.as_view(),
        name="flight-booking-detail",
    ),
    path(
        "travel-requests/<int:travel_request_id>/bookings/hotels/",
        HotelBookingListCreateView.as_view(),
        name="hotel-bookings",
    ),
    path(
        "travel-requests/<int:travel_request_id>/bookings/hotels/<int:booking_id>/",
        HotelBookingDetailView.as_view(),
        name="hotel-booking-detail",
    ),
]
