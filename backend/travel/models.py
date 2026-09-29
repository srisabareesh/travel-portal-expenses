
from django.conf import settings
from django.db import models

# Create your models here.

class Country(models.Model):
    name = models.CharField(
        max_length= 100,
        unique= True
    )

    country_code = models.CharField(
        max_length= 3,
        unique= True
    )

    is_active = models.BooleanField(
        default= True
    )

    created_at = models.DateTimeField(
        auto_now_add= True
    )

    updated_at = models.DateTimeField(
        auto_now= True
    )
    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return f"{self.name} ({self.country_code})"

class TravelRequest(models.Model):
    class TravelType(models.TextChoices):
        BUSINESS = "BUSINESS", "Business"
        TRAINING = "TRAINING", "Training"
        PROJECT = "PROJECT", "Project"
        OTHER = "OTHER", "Other"

        # Phase 3.1: new travel types.
        # Legacy values above are kept so historical
        # records keep working unchanged.
        DOMESTIC = "DOMESTIC", "Domestic"
        INTERNATIONAL = "INTERNATIONAL", "International"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        DOCUMENT_PENDING = "DOCUMENT_PENDING", "Document Pending"
        DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION", "Document Verification"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
    request_number = models.CharField(
        max_length=20,
        unique=True,
        blank= True,
    )
    employee= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name= "travel_requests"
    )
    destination_country=models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="travel_requests"
    )
    destination_city=models.CharField(
        max_length=100
    )
    client=models.CharField(
        max_length=150,
        blank=True
    )
    project=models.CharField(
        max_length=150,
        blank= True
    )
    travel_type=models.CharField(
        max_length=20,
        choices=TravelType.choices

    )
    start_date= models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_at=models.DateTimeField(
        auto_now_add=True
    )
    updated_at=models.DateTimeField(
        auto_now= True
    )

    def save(self, *args, **kwargs):
        if not self.request_number:
            number = 1

            while TravelRequest.objects.filter(
                request_number=f"TR-{number:04d}"
            ).exists():
                number += 1

            self.request_number = f"TR-{number:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.request_number or f"Travel Request {self.pk}"
    