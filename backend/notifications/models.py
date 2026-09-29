from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app notification for a user about a business event.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    event = models.CharField(
        max_length=60,
    )

    message = models.CharField(
        max_length=300,
    )

    travel_request = models.ForeignKey(
        "travel.TravelRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(
        default=False,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ("-created_at", "-id")

        indexes = [
            models.Index(
                fields=["recipient", "is_read"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.recipient_id} {self.event} "
            f"{'read' if self.is_read else 'unread'}"
        )
