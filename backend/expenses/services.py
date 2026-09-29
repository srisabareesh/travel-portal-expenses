from django.db import transaction

from .models import Expense, ExpenseConfiguration, Settlement


def calculate_settlement(travel_request, user):
    """
    Calculate the settlement for a travel request from
    verified expenses, configured allowances and the paid
    advance. Stores all components transparently.

    Net settlement > 0: company owes employee.
    Net settlement < 0: employee owes company.
    """

    config = getattr(
        travel_request,
        "expense_configuration",
        None,
    )

    expenses = travel_request.expenses.all()

    eligible = sum(
        (expense.amount for expense in expenses
         if expense.status == Expense.Status.VERIFIED),
        start=DecimalZero(),
    )

    rejected = sum(
        (expense.amount for expense in expenses
         if expense.status == Expense.Status.REJECTED),
        start=DecimalZero(),
    )

    allowances = DecimalZero()

    if config is not None:

        duration_days = (
            travel_request.end_date
            - travel_request.start_date
        ).days + 1

        if config.daily_allowance is not None:
            allowances += config.daily_allowance * duration_days

        for value in (
            config.food_allowance,
            config.hotel_allowance,
            config.local_transport_allowance,
            config.other_allowance,
        ):
            if value is not None:
                allowances += value

    advance = (
        config.advance_amount
        if (
            config is not None
            and config.advance_paid
            and config.advance_amount is not None
        )
        else DecimalZero()
    )

    net = eligible + allowances - advance

    with transaction.atomic():

        settlement, _created = (
            Settlement.objects.get_or_create(
                travel_request=travel_request,
                defaults={},
            )
        )

        settlement.eligible_expenses_total = eligible
        settlement.rejected_expenses_total = rejected
        settlement.allowances_total = allowances
        settlement.advance_paid = advance
        settlement.net_settlement = net
        settlement.currency = (
            config.currency
            if config is not None
            else ""
        )
        settlement.calculated_by = user

        settlement.save()

    return settlement


def DecimalZero():
    from decimal import Decimal

    return Decimal("0")
