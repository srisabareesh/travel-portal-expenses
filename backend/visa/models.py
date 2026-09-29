from django.db import models

from travel.models import TravelRequest
from users.models import User


class Visa(models.Model):
    """
    Visa tracking for international travel requests.

    Visa state is intentionally stored here, separate from
    TravelRequest.status, so the request lifecycle and the
    visa lifecycle can evolve independently.
    """

    class State(models.TextChoices):
        NOT_APPLIED = "NOT_APPLIED", "Not Applied"
        APPLIED = "APPLIED", "Applied"
        UNDER_PROCESS = "UNDER_PROCESS", "Under Process"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    travel_request = models.OneToOneField(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name="visa",
    )

    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.NOT_APPLIED,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=(
            "Country the visa is applied for. Defaults "
            "to the destination country name."
        ),
    )

    applied_on = models.DateField(
        null=True,
        blank=True,
    )

    decision_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    decided_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visa_decisions",
    )

    remarks = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Visa"
        verbose_name_plural = "Visas"

    def __str__(self):
        return (
            f"{self.travel_request.request_number} - "
            f"{self.state}"
        )
