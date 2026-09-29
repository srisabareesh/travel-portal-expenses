from django.urls import path

from .views import (
    ExpenseConfigurationView,
    ExpenseListCreateView,
    ExpenseVerifyView,
    SettlementActionView,
    SettlementCalculateView,
    SettlementView,
)


urlpatterns = [
    path(
        "travel-requests/<int:travel_request_id>/expense-configuration/",
        ExpenseConfigurationView.as_view(),
        name="expense-configuration",
    ),
    path(
        "travel-requests/<int:travel_request_id>/expenses/",
        ExpenseListCreateView.as_view(),
        name="expenses",
    ),
    path(
        "travel-requests/<int:travel_request_id>/expenses/<int:expense_id>/verify/",
        ExpenseVerifyView.as_view(),
        name="expense-verify",
    ),
    path(
        "travel-requests/<int:travel_request_id>/settlement/",
        SettlementView.as_view(),
        name="settlement-detail",
    ),
    path(
        "travel-requests/<int:travel_request_id>/settlement/calculate/",
        SettlementCalculateView.as_view(),
        name="settlement-calculate",
    ),
    path(
        "travel-requests/<int:travel_request_id>/settlement/<str:action>/",
        SettlementActionView.as_view(),
        name="settlement-action",
    ),
]
