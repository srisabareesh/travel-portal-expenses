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