from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import EmployeeDocument
from documents.services import (
    update_travel_request_document_status,
)

from .models import Verification
from .serializers import VerificationSerializer
from users.permissions import IsReviewerOrManager


class DocumentVerificationView(APIView):

    permission_classes = [IsReviewerOrManager]

    def post(self, request, document_id):

        document = get_object_or_404(
            EmployeeDocument,
            id=document_id,
        )

        verification_status = request.data.get(
            "status"
        )

        comments = request.data.get(
            "comments",
            "",
        )

        if verification_status not in (
            Verification.Status.APPROVED,
            Verification.Status.REJECTED,
        ):
            return Response(
                {
                    "detail": (
                        "Status must be APPROVED "
                        "or REJECTED."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            verification_status
            == Verification.Status.REJECTED
            and not comments.strip()
        ):
            return Response(
                {
                    "detail": (
                        "Comments are required "
                        "when rejecting a document."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reviewer = request.user

        verification = Verification.objects.create(
            document=document,
            reviewer=reviewer,
            status=verification_status,
            comments=comments,
        )

        if (
            verification_status
            == Verification.Status.APPROVED
        ):
            document.status = (
                EmployeeDocument.Status.VERIFIED
            )

        else:
            document.status = (
                EmployeeDocument.Status.REJECTED
            )

        document.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        update_travel_request_document_status(
            document.travel_request
        )

        serializer = VerificationSerializer(
            verification
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class DocumentVerificationHistoryView(APIView):

    permission_classes = [IsReviewerOrManager]

    def get(self, request, document_id):

        document = get_object_or_404(
            EmployeeDocument,
            id=document_id,
        )

        verifications = (
            Verification.objects
            .filter(document=document)
            .select_related("reviewer")
            .order_by("-verified_at")
        )

        serializer = VerificationSerializer(
            verifications,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )