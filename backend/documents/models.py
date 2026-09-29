from django.db import models

from travel.models import Country


class DocumentType(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.name


class DocumentRequirement(models.Model):
    """
    Defines which documents are required
    for a particular country and travel type.
    """

    class TravelType(models.TextChoices):
        BUSINESS = "BUSINESS", "Business"
        TRAINING = "TRAINING", "Training"
        PROJECT = "PROJECT", "Project"
        OTHER = "OTHER", "Other"

        # Phase 3.1: new travel types, kept in sync
        # with TravelRequest.TravelType so requirements
        # can match the new travel requests.
        # Legacy values above are kept so historical
        # requirements keep working unchanged.
        DOMESTIC = "DOMESTIC", "Domestic"
        INTERNATIONAL = "INTERNATIONAL", "International"

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="document_requirements"
    )

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE,
        related_name="requirements"
    )

    travel_type = models.CharField(
        max_length=20,
        choices=TravelType.choices
    )

    mandatory = models.BooleanField(
        default=True
    )

    minimum_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    maximum_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.country.name} - "
            f"{self.document_type.name} - "
            f"{self.travel_type}"
        )


class EmployeeDocument(models.Model):

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        EXPIRING_SOON = "EXPIRING_SOON", "Expiring Soon"

    travel_request = models.ForeignKey(
        "travel.TravelRequest",
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.ForeignKey(
        "DocumentType",
        on_delete=models.PROTECT,
        related_name="employee_documents"
    )

    file = models.FileField(
        upload_to="travel_documents/"
    )

    issue_date = models.DateField(
        null=True,
        blank=True
    )

    expiry_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED
    )

    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="uploaded_documents"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.travel_request.request_number} - "
            f"{self.document_type.name}"
        )