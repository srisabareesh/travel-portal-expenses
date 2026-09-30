from django.db import models

from travel.models import TravelRequest


class FlightBooking(models.Model):
    """
    Flight booking information for a travel request.

    Booking data is captured after approvals, never on the
    initial request form.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"

    travel_request = models.ForeignKey(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name="flight_bookings",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    airline = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    flight_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    booking_reference = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )

    departure_datetime = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrival_datetime = models.DateTimeField(
        null=True,
        blank=True,
    )

    origin = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    destination = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    ##Phase 21 (additive migration): free-form notes from
    ##the reviewer recording the booking.
    notes = models.TextField(
        blank=True,
        default="",
    )

    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
        default="",
    )

    recorded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flight_bookings_recorded",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Flight Booking"
        verbose_name_plural = "Flight Bookings"

    def __str__(self):
        return (
            f"{self.travel_request.request_number} - "
            f"Flight {self.booking_reference or self.status}"
        )


class HotelBooking(models.Model):
    """
    Hotel booking information belonging to a travel request.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"

    travel_request = models.ForeignKey(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name="hotel_bookings",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    hotel_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    booking_reference = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )

    check_in = models.DateField(
        null=True,
        blank=True,
    )

    check_out = models.DateField(
        null=True,
        blank=True,
    )

    location = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    ##Phase 21 (additive migration): the hotel's address.
    address = models.TextField(
        blank=True,
        default="",
    )

    ##Phase 21 (additive migration): free-form notes from
    ##the reviewer recording the booking.
    notes = models.TextField(
        blank=True,
        default="",
    )

    room_details = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
        default="",
    )

    recorded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hotel_bookings_recorded",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Hotel Booking"
        verbose_name_plural = "Hotel Bookings"

    def __str__(self):
        return (
            f"{self.travel_request.request_number} - "
            f"Hotel {self.hotel_name or self.status}"
        )
