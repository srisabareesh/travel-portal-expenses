from django.db import models

from travel.models import TravelRequest


class ExpenseConfiguration(models.Model):
    """
    Approved expense limits and advance configured by
    authorized users AFTER approval/booking - never part of
    the initial travel request.
    """

    travel_request = models.OneToOneField(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name="expense_configuration",
    )

    max_approved_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum total approved expenses.",
    )

    advance_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Advance amount given to the employee.",
    )

    daily_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    food_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    hotel_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    local_transport_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    other_allowance = models.DecimalField(
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

    advance_paid = models.BooleanField(
        default=False,
    )

    advance_payment_date = models.DateField(
        null=True,
        blank=True,
    )

    advance_payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    configured_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expense_configurations",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"Expense config for "
            f"{self.travel_request.request_number}"
        )


class Expense(models.Model):
    """
    An expense line submitted by the employee for a
    travel request.
    """

    class Category(models.TextChoices):
        FOOD = "FOOD", "Food"
        HOTEL = "HOTEL", "Hotel"
        TRANSPORTATION = "TRANSPORTATION", "Transportation"
        VISA = "VISA", "Visa"
        LOCAL_TRAVEL = "LOCAL_TRAVEL", "Local Travel"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    travel_request = models.ForeignKey(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name="expenses",
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )

    expense_date = models.DateField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
        default="",
    )

    description = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )

    receipt = models.FileField(
        upload_to="expense_receipts/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )

    submitted_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="submitted_expenses",
    )

    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_expenses",
    )

    review_comments = models.TextField(
        blank=True,
        default="",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ("expense_date", "id")

    def __str__(self):
        return (
            f"{self.travel_request.request_number} - "
            f"{self.category} {self.amount}"
        )


class Settlement(models.Model):
    """
    Settlement for a travel request with transparent,
    stored calculation components (not just a final number).
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_APPROVAL = "IN_APPROVAL", "In Approval"
        APPROVED = "APPROVED", "Approved"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"

    travel_request = models.OneToOneField(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name="settlement",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    eligible_expenses_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    rejected_expenses_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    allowances_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    advance_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    net_settlement = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Positive: company owes employee. "
            "Negative: employee owes company."
        ),
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
        default="",
    )

    calculated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settlements_calculated",
    )

    approved_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settlements_approved",
    )

    processed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settlements_processed",
    )

    payment_date = models.DateField(
        null=True,
        blank=True,
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    payment_method = models.CharField(
        max_length=80,
        blank=True,
        default="",
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

    def __str__(self):
        return (
            f"Settlement {self.travel_request.request_number}"
            f" - {self.net_settlement} {self.currency}"
        )
