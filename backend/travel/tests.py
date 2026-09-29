"""
Phase 3.1 foundation tests.

Covers:
    * New travel types DOMESTIC / INTERNATIONAL
    * Legacy travel types remain valid and unchanged
    * Serializer accepts new types and still rejects invalid values
    * Existing travel requests are not converted or modified
"""

from datetime import date

from django.test import TestCase

from rest_framework.exceptions import ValidationError

from users.models import User

from .models import Country, TravelRequest
from .serializers import TravelRequestSerializer


def make_travel_request(travel_type):
    """Create a minimal travel request with the given travel type."""

    country = Country.objects.create(
        name=f"Country-{travel_type}",
        country_code=travel_type[:2],
    )

    user = User.objects.create_user(
        username=f"employee-{travel_type}",
        password="TestPassword123",
    )

    return TravelRequest.objects.create(
        employee=user,
        destination_country=country,
        destination_city="Test City",
        travel_type=travel_type,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        purpose="Phase 3.1 foundation test",
        status="DRAFT",
    )


class TravelTypeChoicesTests(TestCase):
    """The travel type enumeration must support old and new values."""

    def test_new_travel_types_exist(self):

        self.assertEqual(
            TravelRequest.TravelType.DOMESTIC,
            "DOMESTIC",
        )

        self.assertEqual(
            TravelRequest.TravelType.DOMESTIC.label,
            "Domestic",
        )

        self.assertEqual(
            TravelRequest.TravelType.INTERNATIONAL,
            "INTERNATIONAL",
        )

        self.assertEqual(
            TravelRequest.TravelType.INTERNATIONAL.label,
            "International",
        )

    def test_legacy_travel_types_are_preserved(self):
        ##Historical records rely on these values staying
        ##exactly as they are.

        self.assertEqual(
            TravelRequest.TravelType.BUSINESS,
            "BUSINESS",
        )
        self.assertEqual(
            TravelRequest.TravelType.TRAINING,
            "TRAINING",
        )
        self.assertEqual(
            TravelRequest.TravelType.PROJECT,
            "PROJECT",
        )
        self.assertEqual(
            TravelRequest.TravelType.OTHER,
            "OTHER",
        )

    def test_choices_include_legacy_and_new_values(self):

        values = {
            value
            for value, label in (
                TravelRequest.TravelType.choices
            )
        }

        self.assertEqual(
            values,
            {
                "BUSINESS",
                "TRAINING",
                "PROJECT",
                "OTHER",
                "DOMESTIC",
                "INTERNATIONAL",
            },
        )


class TravelTypePersistenceTests(TestCase):
    """Travel requests must persist both legacy and new types."""

    def test_new_travel_type_is_persisted(self):

        travel_request = make_travel_request(
            TravelRequest.TravelType.DOMESTIC
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "DOMESTIC",
        )

    def test_new_international_travel_type_is_persisted(self):

        travel_request = make_travel_request(
            TravelRequest.TravelType.INTERNATIONAL
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "INTERNATIONAL",
        )

    def test_existing_legacy_request_is_unchanged(self):
        ##Historical requests keep their original type:
        ##no automatic conversion may happen.

        travel_request = make_travel_request(
            TravelRequest.TravelType.BUSINESS
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "BUSINESS",
        )

        self.assertNotEqual(
            travel_request.travel_type,
            "INTERNATIONAL",
        )


class TravelRequestSerializerTravelTypeTests(TestCase):
    """The API layer must accept the new types like the old ones."""

    def setUp(self):

        self.user = User.objects.create_user(
            username="serializer-employee",
            password="TestPassword123",
        )

        self.country = Country.objects.create(
            name="Serializer Land",
            country_code="SL",
        )

        self.base_payload = {
            "destination_country": self.country.id,
            "destination_city": "Test City",
            "travel_type": TravelRequest.TravelType.DOMESTIC,
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
            "purpose": "Serializer travel-type test",
        }

    def test_serializer_accepts_domestic(self):

        serializer = TravelRequestSerializer(
            data=self.base_payload
        )

        self.assertTrue(serializer.is_valid())

    def test_serializer_accepts_international(self):

        payload = {
            **self.base_payload,
            "travel_type": (
                TravelRequest.TravelType.INTERNATIONAL
            ),
        }

        serializer = TravelRequestSerializer(data=payload)

        self.assertTrue(serializer.is_valid())

    def test_serializer_accepts_legacy_business(self):

        payload = {
            **self.base_payload,
            "travel_type": (
                TravelRequest.TravelType.BUSINESS
            ),
        }

        serializer = TravelRequestSerializer(data=payload)

        self.assertTrue(serializer.is_valid())

    def test_serializer_rejects_invalid_travel_type(self):

        payload = {
            **self.base_payload,
            "travel_type": "NOT_A_TYPE",
        }

        serializer = TravelRequestSerializer(data=payload)

        self.assertFalse(serializer.is_valid())

        self.assertIn("travel_type", serializer.errors)

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
