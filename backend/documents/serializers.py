from rest_framework import serializers

from .models import EmployeeDocument


class EmployeeDocumentSerializer(
    serializers.ModelSerializer
):

    document_type_name = serializers.CharField(
        source="document_type.name",
        read_only=True,
    )

    class Meta:

        model = EmployeeDocument

        fields = (
            "id",
            "travel_request",
            "document_type",
            "document_type_name",
            "file",
            "issue_date",
            "expiry_date",
            "status",
            "uploaded_by",
            "uploaded_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "status",
            "uploaded_by",
            "uploaded_at",
            "updated_at",            
        )

    def validate_file(self, value):
        """
        Validate uploaded document file.
        """

        max_size = 10 * 1024 * 1024  # 10 MB

        if value.size > max_size:
            raise serializers.ValidationError(
                "File size cannot exceed 10 MB."
            )

        allowed_extensions = (
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
        )

        file_name = value.name.lower()

        if not file_name.endswith(
            allowed_extensions
        ):
            raise serializers.ValidationError(
                "Only PDF, JPG, JPEG and PNG files are allowed."
            )

        return value

    def validate(self, attrs):
        """
        Validate document dates.
        """

        issue_date = attrs.get("issue_date")
        expiry_date = attrs.get("expiry_date")

        if (
            issue_date is not None
            and expiry_date is not None
            and expiry_date < issue_date
        ):
            raise serializers.ValidationError(
                {
                    "expiry_date": (
                        "Expiry date cannot be earlier "
                        "than issue date."
                    )
                }
            )

        return attrs


class DocumentChecklistSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    document_type_id = serializers.IntegerField()
    mandatory = serializers.BooleanField()
    status = serializers.CharField()
    document_id = serializers.IntegerField(allow_null=True)
    file = serializers.CharField(allow_null=True)
    issue_date = serializers.DateField(allow_null=True)
    expiry_date = serializers.DateField(allow_null=True)