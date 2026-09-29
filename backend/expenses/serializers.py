from rest_framework import serializers

from .models import Expense, ExpenseConfiguration, Settlement


class ExpenseConfigurationSerializer(
    serializers.ModelSerializer
):

    configured_by_name = serializers.CharField(
        source="configured_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = ExpenseConfiguration

        fields = (
            "id",
            "travel_request",
            "max_approved_expenses",
            "advance_amount",
            "daily_allowance",
            "food_allowance",
            "hotel_allowance",
            "local_transport_allowance",
            "other_allowance",
            "currency",
            "advance_paid",
            "advance_payment_date",
            "advance_payment_reference",
            "configured_by",
            "configured_by_name",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "configured_by",
            "created_at",
            "updated_at",
        )


class ExpenseSerializer(serializers.ModelSerializer):

    submitted_by_name = serializers.CharField(
        source="submitted_by.get_full_name",
        read_only=True,
    )

    reviewed_by_name = serializers.CharField(
        source="reviewed_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Expense

        fields = (
            "id",
            "travel_request",
            "category",
            "expense_date",
            "amount",
            "currency",
            "description",
            "receipt",
            "status",
            "submitted_by",
            "submitted_by_name",
            "reviewed_by",
            "reviewed_by_name",
            "review_comments",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "status",
            "submitted_by",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

    def validate_amount(self, value):

        if value is None or value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        return value

    def validate_category(self, value):

        if value not in Expense.Category.values:
            raise serializers.ValidationError(
                "Category must be one of: "
                + ", ".join(Expense.Category.values)
                + "."
            )

        return value

    def validate(self, attrs):

        request = self.context.get("request")

        travel_request = (
            self.context.get("travel_request")
        )

        if (
            request is not None
            and travel_request is not None
            and request.method == "POST"
        ):

            ##Ownership is enforced by the view; here we
            ##keep duplicate-submission protection simple
            ##and only validate the basics.

            pass

        expense_date = attrs.get("expense_date")

        if (
            travel_request is not None
            and expense_date is not None
        ):

            if (
                expense_date
                < travel_request.start_date
            ):
                raise serializers.ValidationError(
                    {
                        "expense_date": (
                            "Expense date cannot be before "
                            "the travel start date."
                        )
                    }
                )

        return attrs


class SettlementSerializer(
    serializers.ModelSerializer
):

    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name",
        read_only=True,
    )

    processed_by_name = serializers.CharField(
        source="processed_by.get_full_name",
        read_only=True,
    )

    calculated_by_name = serializers.CharField(
        source="calculated_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Settlement

        fields = (
            "id",
            "travel_request",
            "status",
            "eligible_expenses_total",
            "rejected_expenses_total",
            "allowances_total",
            "advance_paid",
            "net_settlement",
            "currency",
            "calculated_by",
            "calculated_by_name",
            "approved_by",
            "approved_by_name",
            "processed_by",
            "processed_by_name",
            "payment_date",
            "payment_reference",
            "payment_method",
            "remarks",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "status",
            "eligible_expenses_total",
            "rejected_expenses_total",
            "allowances_total",
            "advance_paid",
            "net_settlement",
            "currency",
            "calculated_by",
            "approved_by",
            "processed_by",
            "created_at",
            "updated_at",
        )
