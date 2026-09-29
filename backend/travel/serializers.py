from rest_framework import serializers

from .models import Country, TravelRequest
from .services import (
    is_legacy_travel_type,
    is_new_travel_type,
)


class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = Country

        fields = (
            "id",
            "name",
            "country_code",
            "is_active",
        )


class TravelRequestSerializer(
    serializers.ModelSerializer
):

    employee_name = serializers.CharField(
        source="employee.get_full_name",
        read_only=True,
    )

    country_name = serializers.CharField(
        source="destination_country.name",
        read_only=True,
    )

    ##Read-only compatibility flag so clients can tell
    ##historical (legacy) classifications from new ones
    ##without hard-coding the legacy values themselves.
    travel_type_is_legacy = serializers.SerializerMethodField()

    class Meta:
        model = TravelRequest

        fields = (
            "id",
            "request_number",
            "employee",
            "employee_name",
            "destination_country",
            "country_name",
            "destination_city",
            "client",
            "project",
            "travel_type",
            "travel_type_is_legacy",
            "start_date",
            "end_date",
            "purpose",
            "status",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "employee",
            "request_number",
            "status",
            "created_at",
            "updated_at",
        )

        ##Not required at the serializer level so that
        ##updates of existing records can omit the field
        ##entirely; create-time presence and validity are
        ##enforced in validate() below.
        extra_kwargs = {
            "travel_type": {
                "required": False,
            },
        }

    def get_travel_type_is_legacy(self, obj):

        return is_legacy_travel_type(obj.travel_type)

    def validate_travel_type(self, value):
        """
        Travel-type validation rules:

        1. Creating a new request:
           only the new DOMESTIC / INTERNATIONAL
           travel types are accepted.

        2. Updating an existing historical request:
           the stored value is protected. The field
           is simply not in the update payload, so
           the record keeps its legacy value and
           stays readable and usable.

        3. Reclassifying an existing record:
           only an explicit change to one of the new
           travel types is accepted, and only when
           the caller sends the field. Legacy values
           can never be (re)assigned.

        4. The value itself must always be a valid
           choice on the model.
        """

        if value not in TravelRequest.TravelType.values:

            raise serializers.ValidationError(
                "Travel type must be one of: "
                + ", ".join(TravelRequest.TravelType.values)
                + "."
            )

        instance = getattr(self, "instance", None)

        is_create = instance is None

        if is_create:

            if is_legacy_travel_type(value):

                raise serializers.ValidationError(
                    "New travel requests must use "
                    "DOMESTIC or INTERNATIONAL. "
                    "Legacy travel types are reserved "
                    "for historical records."
                )

            return value

        ##Update of an existing record.

        if value == instance.travel_type:

            ##Re-sending the stored value (including a
            ##historical legacy value) is an idempotent
            ##no-op: the record keeps its classification
            ##and nothing is converted.
            return value

        if is_legacy_travel_type(value):

            raise serializers.ValidationError(
                "Legacy travel types are reserved for "
                "historical records and cannot be assigned."
            )

        if not is_new_travel_type(value):

            raise serializers.ValidationError(
                "Travel type must be one of: "
                + ", ".join(TravelRequest.TravelType.values)
                + "."
            )

        ##Explicit reclassification of an existing
        ##record to a new travel type.
        return value

    def validate(self, attrs):

        if self.instance is None:

            ##Creation: the travel type is mandatory and
            ##(via validate_travel_type) must be a new
            ##DOMESTIC / INTERNATIONAL value.
            if "travel_type" not in attrs:

                raise serializers.ValidationError(
                    {
                        "travel_type": (
                            "This field is required."
                        )
                    }
                )

        else:

            ##Update: when the field is omitted the stored
            ##value is kept, so historical records can be
            ##edited without touching their classification.
            if "travel_type" not in attrs:

                attrs["travel_type"] = (
                    self.instance.travel_type
                )

        start_date = attrs.get(
            "start_date"
        )

        end_date = attrs.get(
            "end_date"
        )

        if self.instance is not None:

            ##Phase 3.4: validate the effective date pair.
            ##When only one date is supplied (partial
            ##update), the other falls back to the stored
            ##value so a PATCH cannot make the pair
            ##incoherent. When neither date is supplied,
            ##historical records are not forced through
            ##date validation.
            if start_date is None:

                start_date = (
                    self.instance.start_date
                )

            if end_date is None:

                end_date = (
                    self.instance.end_date
                )

            dates_touched = (
                "start_date" in attrs
                or "end_date" in attrs
            )

            if not dates_touched:

                return attrs

        elif start_date is None:

            raise serializers.ValidationError(
                {
                    "start_date": (
                        "This field is required."
                    )
                }
            )

        elif end_date is None:

            raise serializers.ValidationError(
                {
                    "end_date": (
                        "This field is required."
                    )
                }
            )

        if (
            start_date is not None
            and end_date is not None
            and end_date < start_date
        ):
            raise serializers.ValidationError(
                {
                    "end_date": (
                        "End date cannot be earlier "
                        "than start date."
                    )
                }
            )

        return attrs
