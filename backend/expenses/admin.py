from django.contrib import admin

from .models import Expense, ExpenseConfiguration, Settlement


@admin.register(ExpenseConfiguration)
class ExpenseConfigurationAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "max_approved_expenses",
        "advance_amount",
        "advance_paid",
        "currency",
        "configured_by",
    )

    search_fields = (
        "travel_request__request_number",
    )


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "category",
        "expense_date",
        "amount",
        "currency",
        "status",
        "submitted_by",
        "reviewed_by",
    )

    list_filter = ("status", "category")

    search_fields = (
        "travel_request__request_number",
        "description",
    )


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "status",
        "eligible_expenses_total",
        "allowances_total",
        "advance_paid",
        "net_settlement",
        "currency",
    )

    list_filter = ("status",)

    search_fields = (
        "travel_request__request_number",
    )
