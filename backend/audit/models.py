from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit record for important business actions.

    Records must not be silently deleted: the admin may only
    view them (no delete action is registered).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=60,
    )

    travel_request = models.ForeignKey(
        "travel.TravelRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    object_repr = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    previous_value = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    new_value = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    comment = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        blank=True,
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ("-created_at", "-id")

        verbose_name = "Audit log entry"
        verbose_name_plural = "Audit log entries"

    def __str__(self):
        return (
            f"{self.action} by "
            f"{self.user_id} at {self.created_at:%Y-%m-%d %H:%M}"
        )
