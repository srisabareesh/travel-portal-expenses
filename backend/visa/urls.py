from django.urls import path

from .views import (
    VisaApplyView,
    VisaDecisionView,
    VisaDetailView,
)


urlpatterns = [
    path(
        "travel-requests/<int:travel_request_id>/visa/",
        VisaDetailView.as_view(),
        name="visa-detail",
    ),
    path(
        "travel-requests/<int:travel_request_id>/visa/apply/",
        VisaApplyView.as_view(),
        name="visa-apply",
    ),
    path(
        "travel-requests/<int:travel_request_id>/visa/decision/",
        VisaDecisionView.as_view(),
        name="visa-decision",
    ),
]
