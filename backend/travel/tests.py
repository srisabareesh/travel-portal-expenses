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

    def test_serializer_rejects_legacy_business_on_create(self):
        ##Phase 3.2 business rule: new requests must use
        ##DOMESTIC / INTERNATIONAL. The Phase 3.1 test
        ##accepting BUSINESS on create was intentionally
        ##replaced by this rejection test.

        payload = {
            **self.base_payload,
            "travel_type": (
                TravelRequest.TravelType.BUSINESS
            ),
        }

        serializer = TravelRequestSerializer(data=payload)

        self.assertFalse(serializer.is_valid())

        self.assertIn("travel_type", serializer.errors)

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


## -----------------------------------------------------------------
## Phase 3.2: existing-data-safe travel type handling
## -----------------------------------------------------------------

import json

from rest_framework_simplejwt.tokens import RefreshToken

from .services import (
    is_legacy_travel_type,
    is_new_travel_type,
)


class TravelTypeHelperTests(TestCase):
    """The central compatibility helpers classify values correctly."""

    def test_is_legacy_travel_type(self):

        for value in (
            "BUSINESS",
            "TRAINING",
            "PROJECT",
            "OTHER",
        ):

            self.assertTrue(
                is_legacy_travel_type(value)
            )

        self.assertFalse(
            is_legacy_travel_type("DOMESTIC")
        )

        self.assertFalse(
            is_legacy_travel_type("INTERNATIONAL")
        )

    def test_is_new_travel_type(self):

        self.assertTrue(
            is_new_travel_type("DOMESTIC")
        )

        self.assertTrue(
            is_new_travel_type("INTERNATIONAL")
        )

        for value in (
            "BUSINESS",
            "TRAINING",
            "PROJECT",
            "OTHER",
        ):

            self.assertFalse(
                is_new_travel_type(value)
            )


class LegacyTravelTypeReadabilityTests(TestCase):
    """
    Historical records with legacy travel types must
    remain readable and must never be converted.
    """

    def setUp(self):

        self.country = Country.objects.create(
            name="Legacy Land",
            country_code="LL",
        )

    def _create_request(
        self,
        travel_type,
        suffix,
    ):

        user = User.objects.create_user(
            username=f"legacy-employee-{suffix}",
            password="TestPassword123",
        )

        return TravelRequest.objects.create(
            employee=user,
            destination_country=self.country,
            destination_city="Legacy City",
            travel_type=travel_type,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 15),
            purpose="Historical request",
            status="DRAFT",
        )

    def test_existing_business_request_remains_readable(self):

        travel_request = self._create_request(
            "BUSINESS",
            "business",
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "BUSINESS",
        )

        serializer = TravelRequestSerializer(
            travel_request
        )

        self.assertEqual(
            serializer.data["travel_type"],
            "BUSINESS",
        )

        self.assertTrue(
            serializer.data["travel_type_is_legacy"]
        )

    def test_existing_training_request_remains_readable(self):

        travel_request = self._create_request(
            "TRAINING",
            "training",
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "TRAINING",
        )

        serializer = TravelRequestSerializer(
            travel_request
        )

        self.assertEqual(
            serializer.data["travel_type"],
            "TRAINING",
        )

        self.assertTrue(
            serializer.data["travel_type_is_legacy"]
        )

    def test_existing_project_request_remains_readable(self):

        travel_request = self._create_request(
            "PROJECT",
            "project",
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "PROJECT",
        )

        serializer = TravelRequestSerializer(
            travel_request
        )

        self.assertEqual(
            serializer.data["travel_type"],
            "PROJECT",
        )

        self.assertTrue(
            serializer.data["travel_type_is_legacy"]
        )

    def test_existing_other_request_remains_readable(self):

        travel_request = self._create_request(
            "OTHER",
            "other",
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.travel_type,
            "OTHER",
        )

        serializer = TravelRequestSerializer(
            travel_request
        )

        self.assertEqual(
            serializer.data["travel_type"],
            "OTHER",
        )

        self.assertTrue(
            serializer.data["travel_type_is_legacy"]
        )

    def test_legacy_values_are_not_automatically_converted(self):
        ##No automatic classification may happen: every
        ##legacy value must survive save/refresh cycles.

        for travel_type in (
            "BUSINESS",
            "TRAINING",
            "PROJECT",
            "OTHER",
        ):

            travel_request = self._create_request(
                travel_type,
                travel_type.lower(),
            )

            travel_request.refresh_from_db()

            self.assertEqual(
                travel_request.travel_type,
                travel_type,
            )

            self.assertNotEqual(
                travel_request.travel_type,
                "DOMESTIC",
            )

            self.assertNotEqual(
                travel_request.travel_type,
                "INTERNATIONAL",
            )


class TravelRequestCreateTravelTypeTests(TestCase):
    """
    New requests accept only DOMESTIC / INTERNATIONAL
    and reject every legacy value (API level).
    """

    def setUp(self):

        self.employee = User.objects.create_user(
            username="new-requests-employee",
            password="TestPassword123",
        )

        self.country = Country.objects.create(
            name="New Land",
            country_code="NL",
        )

        self.base_payload = {
            "destination_country": self.country.id,
            "destination_city": "New City",
            "client": "Client A",
            "project": "Project A",
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
            "purpose": "Phase 3.2 creation test",
        }

    def _auth(self, user):

        return (
            "Bearer "
            + str(
                RefreshToken.for_user(
                    user
                ).access_token
            )
        )

    def _post_create(self, travel_type):

        payload = {
            **self.base_payload,
            "travel_type": travel_type,
        }

        return self.client.post(
            "/api/travel-requests/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=self._auth(
                self.employee
            ),
        )

    def test_api_create_accepts_domestic(self):

        response = self._post_create("DOMESTIC")

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertFalse(
            response.data["travel_type_is_legacy"]
        )

        travel_request = TravelRequest.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            travel_request.travel_type,
            "DOMESTIC",
        )

    def test_api_create_accepts_international(self):

        response = self._post_create("INTERNATIONAL")

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertFalse(
            response.data["travel_type_is_legacy"]
        )

        travel_request = TravelRequest.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            travel_request.travel_type,
            "INTERNATIONAL",
        )

    def test_api_create_rejects_business(self):

        response = self._post_create("BUSINESS")

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "travel_type",
            response.data,
        )

    def test_api_create_rejects_training(self):

        response = self._post_create("TRAINING")

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "travel_type",
            response.data,
        )

    def test_api_create_rejects_project(self):

        response = self._post_create("PROJECT")

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "travel_type",
            response.data,
        )

    def test_api_create_rejects_other(self):

        response = self._post_create("OTHER")

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "travel_type",
            response.data,
        )


class TravelRequestUpdateTravelTypeTests(TestCase):
    """
    Updates of existing records must never break
    historical values.
    """

    def setUp(self):

        self.employee = User.objects.create_user(
            username="update-employee",
            password="TestPassword123",
        )

        self.country = Country.objects.create(
            name="Update Land",
            country_code="UL",
        )

        self.legacy_request = TravelRequest.objects.create(
            employee=self.employee,
            destination_country=self.country,
            destination_city="Update City",
            client="Client U",
            project="Project U",
            travel_type="BUSINESS",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 5),
            purpose="Historical update test",
            status="DRAFT",
        )

    def _auth(self, user):

        return (
            "Bearer "
            + str(
                RefreshToken.for_user(
                    user
                ).access_token
            )
        )

    def _put_update(self, travel_request, **overrides):

        payload = {
            "destination_country": self.country.id,
            "destination_city": (
                travel_request.destination_city
            ),
            "client": travel_request.client,
            "project": travel_request.project,
            "start_date": "2026-02-01",
            "end_date": "2026-02-05",
            "purpose": travel_request.purpose,
        }

        payload.update(overrides)

        return self.client.put(
            f"/api/travel-requests/{travel_request.pk}/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=self._auth(
                self.employee
            ),
        )

    def test_update_without_travel_type_keeps_legacy_value(self):
        ##Editing a historical record without touching the
        ##travel type keeps the stored legacy value.

        response = self._put_update(
            self.legacy_request,
            destination_city="Edited City",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.legacy_request.refresh_from_db()

        self.assertEqual(
            self.legacy_request.travel_type,
            "BUSINESS",
        )

        self.assertEqual(
            self.legacy_request.destination_city,
            "Edited City",
        )

    def test_resending_stored_legacy_value_is_idempotent_noop(self):
        ##Re-sending the stored legacy value (e.g. a client
        ##echoing the record back) must not convert or
        ##reject: it is an idempotent no-op.

        response = self._put_update(
            self.legacy_request,
            travel_type="BUSINESS",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.legacy_request.refresh_from_db()

        self.assertEqual(
            self.legacy_request.travel_type,
            "BUSINESS",
        )

        self.assertTrue(
            response.data["travel_type_is_legacy"]
        )

    def test_assigning_different_legacy_value_is_rejected(self):
        ##Legacy values can never be (re)assigned: switching
        ##one legacy value for another fails, and the
        ##historical record keeps its stored value.

        response = self._put_update(
            self.legacy_request,
            travel_type="OTHER",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.legacy_request.refresh_from_db()

        self.assertEqual(
            self.legacy_request.travel_type,
            "BUSINESS",
        )

    def test_existing_record_can_be_reclassified_to_domestic(self):

        response = self._put_update(
            self.legacy_request,
            travel_type="DOMESTIC",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.legacy_request.refresh_from_db()

        self.assertEqual(
            self.legacy_request.travel_type,
            "DOMESTIC",
        )

    def test_existing_record_can_be_reclassified_to_international(self):

        response = self._put_update(
            self.legacy_request,
            travel_type="INTERNATIONAL",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.legacy_request.refresh_from_db()

        self.assertEqual(
            self.legacy_request.travel_type,
            "INTERNATIONAL",
        )

    def test_new_record_cannot_be_reassigned_a_legacy_value(self):

        new_request = TravelRequest.objects.create(
            employee=self.employee,
            destination_country=self.country,
            destination_city="New City",
            travel_type="DOMESTIC",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 5),
            purpose="New type update test",
            status="DRAFT",
        )

        response = self._put_update(
            new_request,
            travel_type="OTHER",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        new_request.refresh_from_db()

        self.assertEqual(
            new_request.travel_type,
            "DOMESTIC",
        )

    def test_update_validates_unknown_travel_type(self):

        response = self._put_update(
            self.legacy_request,
            travel_type="NOT_A_TYPE",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.legacy_request.refresh_from_db()

        self.assertEqual(
            self.legacy_request.travel_type,
            "BUSINESS",
        )


class TravelRequestApiCompatibilityTests(TestCase):
    """
    Existing retrieval APIs keep returning historical
    records with their legacy travel types.
    """

    def setUp(self):

        self.employee = User.objects.create_user(
            username="api-employee",
            password="TestPassword123",
        )

        self.country = Country.objects.create(
            name="API Land",
            country_code="AL",
        )

        for travel_type in (
            "BUSINESS",
            "TRAINING",
            "PROJECT",
            "OTHER",
        ):

            TravelRequest.objects.create(
                employee=self.employee,
                destination_country=self.country,
                destination_city="API City",
                travel_type=travel_type,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 5),
                purpose=f"API compatibility {travel_type}",
                status="DRAFT",
            )

    def _auth(self, user):

        return (
            "Bearer "
            + str(
                RefreshToken.for_user(
                    user
                ).access_token
            )
        )

    def test_travel_request_list_returns_legacy_records(self):

        response = self.client.get(
            "/api/travel-requests/",
            HTTP_AUTHORIZATION=self._auth(
                self.employee
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            4,
        )

        travel_types = {
            item["travel_type"]
            for item in response.data
        }

        self.assertEqual(
            travel_types,
            {
                "BUSINESS",
                "TRAINING",
                "PROJECT",
                "OTHER",
            },
        )

        self.assertTrue(
            all(
                item["travel_type_is_legacy"]
                for item in response.data
            )
        )

    def test_travel_request_detail_returns_legacy_record(self):

        travel_request = (
            TravelRequest.objects.get(
                employee=self.employee,
                travel_type="BUSINESS",
            )
        )

        response = self.client.get(
            f"/api/travel-requests/{travel_request.pk}/",
            HTTP_AUTHORIZATION=self._auth(
                self.employee
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["travel_type"],
            "BUSINESS",
        )

        self.assertTrue(
            response.data["travel_type_is_legacy"]
        )
