from django.test import TestCase

# Create your tests here.
from datetime import date


from travel.models import Country, TravelRequest
from users.models import User

from .models import DocumentType, DocumentRequirement
from .services import get_document_checklist


class DocumentChecklistTest(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="testemployee",
            password="TestPassword123",
            employee_id="TEST001",
        )

        self.country = Country.objects.create(
            name="Germany",
            country_code="DE",
        )

        self.passport = DocumentType.objects.create(
            name="Passport",
        )

        self.visa = DocumentType.objects.create(
            name="Visa",
        )

        DocumentRequirement.objects.create(
            country=self.country,
            document_type=self.passport,
            travel_type="BUSINESS",
            mandatory=True,
        )

        DocumentRequirement.objects.create(
            country=self.country,
            document_type=self.visa,
            travel_type="BUSINESS",
            mandatory=True,
        )

        self.travel_request = TravelRequest.objects.create(
            employee=self.user,
            destination_country=self.country,
            destination_city="Frankfurt",
            travel_type="BUSINESS",
            start_date=date(2026, 9, 10),
            end_date=date(2026, 12, 10),
            purpose="Client Project",
            status="DRAFT",
        )

    def test_required_documents_are_returned(self):

        checklist = get_document_checklist(
            self.travel_request
        )

        self.assertEqual(
            len(checklist),
            2,
        )

        document_names = {
            item["document_type"]
            for item in checklist
        }

        self.assertIn(
            "Passport",
            document_names,
        )

        self.assertIn(
            "Visa",
            document_names,
        )


class DocumentRequirementNewTravelTypesTest(TestCase):
    """
    Phase 3.1: document requirements must match
    the new DOMESTIC / INTERNATIONAL travel types
    while legacy requirements keep working.
    """

    def setUp(self):

        self.user = User.objects.create_user(
            username="testemployee3",
            password="TestPassword123",
            employee_id="TEST003",
        )

        self.domestic_country = Country.objects.create(
            name="Austria",
            country_code="AT",
        )

        self.international_country = Country.objects.create(
            name="Japan",
            country_code="JP",
        )

        self.id_card = DocumentType.objects.create(
            name="ID Card",
        )

        self.passport = DocumentType.objects.create(
            name="Passport 3",
        )

        self.visa = DocumentType.objects.create(
            name="Visa 3",
        )

        ##Domestic requirement: ID card only.
        DocumentRequirement.objects.create(
            country=self.domestic_country,
            document_type=self.id_card,
            travel_type="DOMESTIC",
            mandatory=True,
        )

        ##International requirements: passport and visa.
        DocumentRequirement.objects.create(
            country=self.international_country,
            document_type=self.passport,
            travel_type="INTERNATIONAL",
            mandatory=True,
        )

        DocumentRequirement.objects.create(
            country=self.international_country,
            document_type=self.visa,
            travel_type="INTERNATIONAL",
            mandatory=True,
        )

    def _make_travel_request(
        self,
        country,
        travel_type,
        username,
    ):

        return TravelRequest.objects.create(
            employee=User.objects.create_user(
                username=username,
                password="TestPassword123",
                employee_id=username.upper(),
            ),
            destination_country=country,
            destination_city="Test City",
            travel_type=travel_type,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 5),
            purpose="Phase 3.1 document requirement test",
            status="DRAFT",
        )

    def test_domestic_request_gets_domestic_requirements(self):

        travel_request = self._make_travel_request(
            self.domestic_country,
            "DOMESTIC",
            "domestic-employee",
        )

        checklist = get_document_checklist(
            travel_request
        )

        document_names = {
            item["document_type"]
            for item in checklist
        }

        self.assertEqual(
            document_names,
            {"ID Card"},
        )

    def test_international_request_gets_international_requirements(self):

        travel_request = self._make_travel_request(
            self.international_country,
            "INTERNATIONAL",
            "international-employee",
        )

        checklist = get_document_checklist(
            travel_request
        )

        document_names = {
            item["document_type"]
            for item in checklist
        }

        self.assertEqual(
            document_names,
            {"Passport 3", "Visa 3"},
        )

    def test_legacy_requirement_matching_unchanged(self):

        travel_request = self._make_travel_request(
            self.domestic_country,
            "BUSINESS",
            "legacy-employee",
        )

        ##Austria only has a DOMESTIC requirement,
        ##so a BUSINESS request gets no requirements.
        ##This proves legacy matching is untouched.
        checklist = get_document_checklist(
            travel_request
        )

        self.assertEqual(
            checklist,
            [],
        )