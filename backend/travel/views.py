from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.services import (
    get_required_documents,
    update_travel_request_document_status,
)

from .models import Country, TravelRequest
from .serializers import (
    CountrySerializer,
    TravelRequestSerializer,
)


class CountryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]


class TravelRequestViewSet(viewsets.ModelViewSet):

    serializer_class = TravelRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        if user.role == "ADMIN":
            return TravelRequest.objects.all()

        if user.role == "REVIEWER":
            return TravelRequest.objects.filter(
                status__in=[
                    TravelRequest.Status.DOCUMENT_PENDING,
                    TravelRequest.Status.DOCUMENT_VERIFICATION,
                ]
            )

        if user.role == "MANAGER":
            return TravelRequest.objects.filter(
                employee__manager=user
            )

        return TravelRequest.objects.filter(
            employee=user
        )

    def perform_create(self, serializer):

        serializer.save(
            employee=self.request.user
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(self, request, pk=None):

        travel_request = get_object_or_404(
            TravelRequest,
            pk=pk,
        )

        # Employee can submit only their own request.
        if (
            request.user.role == "EMPLOYEE"
            and travel_request.employee != request.user
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to submit this travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only DRAFT requests can be submitted.
        if (
            travel_request.status
            != TravelRequest.Status.DRAFT
        ):
            return Response(
                {
                    "detail": (
                        "Only draft travel requests "
                        "can be submitted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        requirements = get_required_documents(
            travel_request
        )

        mandatory_requirements = [
            requirement
            for requirement in requirements
            if requirement.mandatory
        ]

        uploaded_document_type_ids = set(
            travel_request.documents.values_list(
                "document_type_id",
                flat=True,
            )
        )

        missing_mandatory_documents = [
            requirement
            for requirement in mandatory_requirements
            if requirement.document_type_id
            not in uploaded_document_type_ids
        ]

        if missing_mandatory_documents:

            travel_request.status = (
                TravelRequest.Status.DOCUMENT_PENDING
            )

        else:

            travel_request.status = (
                TravelRequest.Status.DOCUMENT_VERIFICATION
            )

        travel_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(
            travel_request
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )