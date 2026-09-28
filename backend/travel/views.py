from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.services import (
    are_all_mandatory_documents_verified,
    get_required_documents,
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

            workflow_requests = TravelRequest.objects.filter(
                status__in=[
                    TravelRequest.Status.DOCUMENT_PENDING,
                    TravelRequest.Status.DOCUMENT_VERIFICATION,
                ]
            )

            own_requests = TravelRequest.objects.filter(
                employee=user
            )

            return (
                workflow_requests
                | own_requests
            ).distinct()

        if user.role == "MANAGER":

            own_requests = TravelRequest.objects.filter(
                employee=user
            )

            team_requests = TravelRequest.objects.filter(
                employee__manager=user
            )

            return (
                own_requests
                | team_requests
            ).distinct()

        return TravelRequest.objects.filter(
            employee=user
        )

    def perform_create(self, serializer):

        serializer.save(
            employee=self.request.user
        )

    def perform_update(self, serializer):

        travel_request = self.get_object()

        if (
            travel_request.employee
            != self.request.user
        ):
            from rest_framework.exceptions import (
                PermissionDenied,
            )

            raise PermissionDenied(
                "You do not have permission "
                "to modify this travel request."
            )

        if (
            travel_request.status
            != TravelRequest.Status.DRAFT
        ):
            from rest_framework.exceptions import (
                ValidationError,
            )

            raise ValidationError(
                {
                    "detail": (
                        "Only draft travel requests "
                        "can be modified."
                    )
                }
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):

        travel_request = self.get_object()

        if (
            travel_request.employee
            != request.user
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to delete this travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            travel_request.status
            != TravelRequest.Status.DRAFT
        ):
            return Response(
                {
                    "detail": (
                        "Only draft travel requests "
                        "can be deleted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
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

        if (
            travel_request.employee
            != request.user
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

        latest_documents = {}

        documents = (
            travel_request.documents
            .all()
            .order_by(
                "-uploaded_at",
                "-id",
            )
        )

        for document in documents:

            if document.document_type_id not in (
                latest_documents
            ):
                latest_documents[
                    document.document_type_id
                ] = document

        missing_mandatory_documents = [
            requirement
            for requirement in mandatory_requirements
            if requirement.document_type_id
            not in latest_documents
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

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):

        travel_request = get_object_or_404(
            TravelRequest,
            pk=pk,
        )

        # Only Managers and Admins can approve.
        if request.user.role not in (
            "MANAGER",
            "ADMIN",
        ):
            return Response(
                {
                    "detail": (
                        "Only managers or admins "
                        "can approve travel requests."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # A Manager cannot approve their own request.
        if (
            request.user.role == "MANAGER"
            and travel_request.employee == request.user
        ):
            return Response(
                {
                    "detail": (
                        "You cannot approve "
                        "your own travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # A Manager can approve only requests
        # belonging to their team.
        if request.user.role == "MANAGER":

            if (
                travel_request.employee.manager
                != request.user
            ):
                return Response(
                    {
                        "detail": (
                            "You do not have permission "
                            "to approve this travel request."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # The request must be in document verification.
        if (
            travel_request.status
            != TravelRequest.Status.DOCUMENT_VERIFICATION
        ):
            return Response(
                {
                    "detail": (
                        "Only travel requests in "
                        "document verification status "
                        "can be approved."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # All mandatory documents must be verified.
        if not are_all_mandatory_documents_verified(
            travel_request
        ):
            return Response(
                {
                    "detail": (
                        "All mandatory documents "
                        "must be verified before "
                        "the travel request can "
                        "be approved."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        travel_request.status = (
            TravelRequest.Status.APPROVED
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

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    def reject(self, request, pk=None):

        travel_request = get_object_or_404(
            TravelRequest,
            pk=pk,
        )

        # Only Managers and Admins can reject.
        if request.user.role not in (
            "MANAGER",
            "ADMIN",
        ):
            return Response(
                {
                    "detail": (
                        "Only managers or admins "
                        "can reject travel requests."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # A Manager cannot reject their own request.
        if (
            request.user.role == "MANAGER"
            and travel_request.employee == request.user
        ):
            return Response(
                {
                    "detail": (
                        "You cannot reject "
                        "your own travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # A Manager can reject only requests
        # belonging to their team.
        if request.user.role == "MANAGER":

            if (
                travel_request.employee.manager
                != request.user
            ):
                return Response(
                    {
                        "detail": (
                            "You do not have permission "
                            "to reject this travel request."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # The request must be in document verification.
        if (
            travel_request.status
            != TravelRequest.Status.DOCUMENT_VERIFICATION
        ):
            return Response(
                {
                    "detail": (
                        "Only travel requests in "
                        "document verification status "
                        "can be rejected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rejection comments are mandatory.
        comments = request.data.get(
            "comments",
            "",
        )

        if not comments.strip():
            return Response(
                {
                    "comments": (
                        "Rejection comments are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        travel_request.status = (
            TravelRequest.Status.REJECTED
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