from django.db import models

from documents.models import EmployeeDocument
from users.models import User


class Verification(models.Model):

    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    document = models.ForeignKey(
        EmployeeDocument,
        on_delete=models.CASCADE,
        related_name="verifications",
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="document_verifications",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )

    comments = models.TextField(
        blank=True,
        default="",
    )

    verified_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.document} - "
            f"{self.status}"
        )