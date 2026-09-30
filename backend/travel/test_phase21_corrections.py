"""
Phase 21 correction pass: end-to-end verification of every
correction requested after real user testing.

Scenarios covered (master specification section 38):

A. International document verification -> MANAGER_APPROVAL
B. Manager approval after reviewer verification
   (regression for the "historical status" bug)
C. Employee permission negatives (review, verify docs,
   approve, bookings, expense verification)
D. Visa: employee-only updates, stage gating, booking
   blocked until APPROVED, rejection stays in stage
E. Booking: reviewer-only creation, employee read-only
F. Expenses: add/verify/reject permissions + currency
   validation
G. Settlement: stage gating, duplicate prevention,
   transitions
H. Workflow progress: current/completed/next action/
   pending role from the backend
I. Domestic: no visa / no international document flow
J. International full flow with documents + visa
"""

from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from rest_framework_simplejwt.tokens import RefreshToken

from bookings.models import FlightBooking, HotelBooking
from documents.models import (
    DocumentRequirement,
    DocumentType,
    EmployeeDocument,
)
from expenses.models import Expense, Settlement
from travel.models import Country, TravelRequest
from users.models import Role, User
from users.services import assign_role, ensure_roles_seeded
from visa.models import Visa


def _auth(user):
    return (
        "Bearer "
        + str(RefreshToken.for_user(user).access_token)
    )


class CorrectionTestBase(TestCase):
    """Shared fixtures for the correction-pass suite."""

    @classmethod
    def setUpTestData(cls):
        ensure_roles_seeded()

        cls.france = Country.objects.create(
            name="Correction France",
            country_code="CF",
        )

        cls.germany = Country.objects.create(
            name="Correction Germany",
            country_code="CG",
        )

        cls.employee = User.objects.create_user(
            username="corr_employee",
            password="TestPassword123",
            role="EMPLOYEE",
            first_name="Corrinne",
            last_name="Employee",
        )

        cls.manager = User.objects.create_user(
            username="corr_manager",
            password="TestPassword123",
            role="MANAGER",
        )

        cls.reviewer = User.objects.create_user(
            username="corr_reviewer",
            password="TestPassword123",
            role="REVIEWER",
        )

        cls.admin = User.objects.create_user(
            username="corr_admin",
            password="TestPassword123",
            role="ADMIN",
        )

        cls.other_employee = User.objects.create_user(
            username="corr_other_employee",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        cls.employee.manager = cls.manager
        cls.employee.save()

        cls.passport = DocumentType.objects.create(
            name="Correction Passport",
        )

        DocumentRequirement.objects.create(
            country=cls.france,
            document_type=cls.passport,
            travel_type="INTERNATIONAL",
            mandatory=True,
        )

    # ---------- helpers ----------

    def _create_request(
        self,
        travel_type="INTERNATIONAL",
        country=None,
        status="DRAFT",
    ):
        return TravelRequest.objects.create(
            employee=self.employee,
            destination_country=country or self.france,
            destination_city="Paris",
            client="Client C",
            project="Project C",
            travel_type=travel_type,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            purpose="Correction pass",
            status=status,
        )

    def _post(self, user, url, data=None):
        return self.client.post(
            url,
            data=data or {},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(user),
        )

    def _get(self, user, url):
        return self.client.get(
            url,
            HTTP_AUTHORIZATION=_auth(user),
        )

    def _upload_document(self, request, document_type):
        return self.client.post(
            f"/api/travel-requests/{request.pk}/documents/upload/",
            data={
                "document_type": document_type.id,
                "file": SimpleUploadedFile(
                    "doc.pdf",
                    b"%PDF-1.4 fake pdf",
                    content_type="application/pdf",
                ),
            },
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

    def _verify_document(self, document_id, decision="APPROVED"):
        return self._post(
            self.reviewer,
            f"/api/documents/{document_id}/verify/",
            {"status": decision, "comments": "ok"},
        )

    def _advance_to_manager_approval(self, request):
        """Submit, review, upload and verify documents."""

        self._post(self.employee, f"/api/travel-requests/{request.pk}/submit/")
        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )

        upload = self._upload_document(request, self.passport)
        self.assertEqual(upload.status_code, 201)

        response = self._verify_document(upload.data["id"])
        self.assertEqual(response.status_code, 201)

        request.refresh_from_db()

        return request

    def _advance_to_visa_processing(self, request):
        """Documents verified -> manager approved -> visa."""

        request = self._advance_to_manager_approval(request)

        self.assertEqual(request.status, "MANAGER_APPROVAL")

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/approve/",
        )
        self.assertEqual(response.status_code, 200)

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-visa/",
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()

        self.assertEqual(request.status, "VISA_PROCESSING")

        return request


class ScenarioATests(CorrectionTestBase):
    """A. International document verification."""

    def test_document_verification_advances_to_manager_approval(self):
        request = self._create_request(status="SUBMITTED")

        self._post(self.employee, f"/api/travel-requests/{request.pk}/submit/")
        request.refresh_from_db()
        self.assertEqual(request.status, "SUBMITTED")

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )
        request.refresh_from_db()
        self.assertEqual(request.status, "DOCUMENTS_PENDING")

        upload = self._upload_document(request, self.passport)
        self.assertEqual(upload.status_code, 201)

        ##Upload moves the request into review.
        request.refresh_from_db()
        self.assertEqual(request.status, "DOCUMENTS_UNDER_REVIEW")

        response = self._verify_document(upload.data["id"])
        self.assertEqual(response.status_code, 201)

        ##All mandatory documents VERIFIED -> the request
        ##moves to MANAGER_APPROVAL automatically.
        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVAL")

    def test_uploading_into_submitted_stays_in_new_vocabulary(self):
        ##Regression: documents uploaded while the request
        ##is SUBMITTED must not flip it into the legacy
        ##DOCUMENT_VERIFICATION status.
        request = self._create_request(status="SUBMITTED")

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )

        self._upload_document(request, self.passport)

        request.refresh_from_db()

        self.assertIn(
            request.status,
            (
                "DOCUMENTS_PENDING",
                "DOCUMENTS_UNDER_REVIEW",
            ),
        )


class ScenarioBTests(CorrectionTestBase):
    """B. Manager approval after reviewer verification."""

    def test_manager_can_approve_after_verification(self):
        request = self._advance_to_manager_approval(self._create_request())

        self.assertEqual(request.status, "MANAGER_APPROVAL")

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], "MANAGER_APPROVED"
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVED")

    def test_manager_cannot_approve_before_documents_verified(self):
        ##Documents uploaded but not verified yet.
        request = self._create_request(status="SUBMITTED")

        self._post(self.employee, f"/api/travel-requests/{request.pk}/submit/")
        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )
        self._upload_document(request, self.passport)

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        ##The request is still in the document stages;
        ##approval is not a valid transition from there.
        self.assertEqual(response.status_code, 400)


class ScenarioCTests(CorrectionTestBase):
    """C. Employee permission negatives (direct API)."""

    def test_employee_cannot_start_review(self):
        request = self._create_request(status="SUBMITTED")

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/start-review/",
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_verify_documents(self):
        request = self._create_request(status="DOCUMENTS_UNDER_REVIEW")

        upload = self._upload_document(request, self.passport)

        response = self._post(
            self.employee,
            f"/api/documents/{upload.data['id']}/verify/",
            {"status": "APPROVED"},
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_approve_request(self):
        request = self._create_request(status="MANAGER_APPROVAL")

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_record_flight_booking(self):
        request = self._create_request(status="MANAGER_APPROVED")

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={
                "airline": "X",
                "booking_reference": "PNR-X",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FlightBooking.objects.count(), 0)

    def test_employee_cannot_record_hotel_booking(self):
        request = self._create_request(status="MANAGER_APPROVED")

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/hotels/",
            data={
                "hotel_name": "X",
                "booking_reference": "HB-X",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(HotelBooking.objects.count(), 0)

    def test_employee_cannot_verify_expenses(self):
        request = self._create_request(status="EXPENSE_SUBMISSION")

        expense = Expense.objects.create(
            travel_request=request,
            category=Expense.Category.FOOD,
            expense_date=date(2026, 12, 2),
            amount="10.00",
            submitted_by=self.employee,
        )

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/expenses/{expense.pk}/verify/",
            {"status": "VERIFIED"},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_is_not_automatically_manager_or_reviewer(self):
        ##ADMIN alone grants no business authority.
        request = self._create_request(status="MANAGER_APPROVAL")

        response = self._post(
            self.admin,
            f"/api/travel-requests/{request.pk}/approve/",
        )
        self.assertEqual(response.status_code, 403)

        response = self._post(
            self.admin,
            f"/api/travel-requests/{request.pk}/start-review/",
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={"status": "BOOKED"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.admin),
        )
        self.assertEqual(response.status_code, 403)

        ##Explicit assignment changes that (business rule).
        assign_role(self.admin, Role.Name.MANAGER)
        self.employee.manager = self.admin
        self.employee.save()

        response = self._post(
            self.admin,
            f"/api/travel-requests/{request.pk}/approve/",
        )
        self.assertEqual(response.status_code, 200)


class ScenarioDTests(CorrectionTestBase):
    """D. Visa rules."""

    def test_reviewer_cannot_update_visa(self):
        request = self._advance_to_visa_processing(
            self._create_request()
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "APPROVED"},
        )

        self.assertEqual(response.status_code, 403)

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/visa/apply/",
            {"applied_on": "2026-12-02"},
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_update_visa_before_stage(self):
        ##Documents not yet verified: no visa updates.
        request = self._create_request(status="DOCUMENTS_UNDER_REVIEW")

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "APPLIED"},
        )

        self.assertEqual(response.status_code, 400)

    def test_booking_unavailable_until_visa_approved(self):
        request = self._advance_to_visa_processing(
            self._create_request()
        )

        ##Visa still NOT_APPLIED: reviewer cannot record
        ##bookings while the request is VISA_PROCESSING.
        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={"status": "BOOKED"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        self.assertEqual(response.status_code, 400)

        ##The employee approves the visa; the request
        ##advances to VISA_APPROVED and booking opens.
        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "APPROVED"},
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "VISA_APPROVED")

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={
                "airline": "Air France",
                "flight_number": "AF101",
                "departure_datetime": "2026-12-01T08:30:00",
                "arrival_datetime": "2026-12-01T10:00:00",
                "origin": "Chennai",
                "destination": "Paris",
                "booking_reference": "PNR-VISA-1",
                "notes": "Window seat requested",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["notes"], "Window seat requested")

    def test_visa_rejection_keeps_request_in_visa_processing(self):
        request = self._advance_to_visa_processing(
            self._create_request()
        )

        self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/apply/",
            {"applied_on": "2026-12-02"},
        )

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "REJECTED"},
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "VISA_PROCESSING")

        ##The employee can re-apply after a rejection.
        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/apply/",
            {"applied_on": "2026-12-03"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "APPLIED")


class ScenarioETests(CorrectionTestBase):
    """E. Booking permissions and real fields."""

    def test_reviewer_can_create_bookings_with_real_fields(self):
        ##Domestic: the booking window opens right after
        ##manager approval (no visa stage).
        request = self._create_request(
            travel_type="DOMESTIC",
            country=self.germany,
            status="MANAGER_APPROVED",
        )

        flight_response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={
                "airline": "Lufthansa",
                "flight_number": "LH760",
                "departure_datetime": "2026-12-01T06:45:00",
                "arrival_datetime": "2026-12-01T09:10:00",
                "origin": "Frankfurt",
                "destination": "Chennai",
                "booking_reference": "QK2P9X",
                "notes": "Arrival transfer arranged",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(flight_response.status_code, 201)
        self.assertEqual(flight_response.data["airline"], "Lufthansa")
        self.assertEqual(flight_response.data["flight_number"], "LH760")
        self.assertEqual(
            flight_response.data["booking_reference"], "QK2P9X"
        )

        hotel_response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/hotels/",
            data={
                "hotel_name": "Taj Coromandel",
                "address": "37 MG Road, Chennai",
                "check_in": "2026-12-01",
                "check_out": "2026-12-05",
                "booking_reference": "HB-99001",
                "notes": "Late check-out confirmed",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(hotel_response.status_code, 201)
        self.assertEqual(hotel_response.data["address"], "37 MG Road, Chennai")
        self.assertEqual(hotel_response.data["notes"], "Late check-out confirmed")

        ##Employee can view.
        response = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/bookings/flights/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_manager_cannot_record_bookings(self):
        request = self._create_request(status="MANAGER_APPROVED")

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={"status": "BOOKED"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.manager),
        )

        self.assertEqual(response.status_code, 403)

    def test_booking_blocked_outside_booking_stage(self):
        ##EXPENSE_VERIFICATION is past the booking window.
        request = self._create_request(status="EXPENSE_VERIFICATION")

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/flights/",
            data={"status": "BOOKED"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        self.assertEqual(response.status_code, 400)


class ScenarioFTests(CorrectionTestBase):
    """F. Expenses: permissions and currency."""

    def test_employee_adds_expense_and_currency_is_validated(self):
        request = self._create_request(status="EXPENSE_SUBMISSION")

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-12-02",
                "amount": "25.50",
                "currency": "usd",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["currency"], "USD")

        ##Free-text currency is rejected.
        response = self.client.post(
            f"/api/travel-requests/{request.pk}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-12-02",
                "amount": "25.50",
                "currency": "DOLLARS",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(response.status_code, 400)

        ##Every supported currency is accepted.
        for code in (
            "INR", "USD", "EUR", "GBP", "AED",
            "SGD", "AUD", "CAD", "JPY",
        ):
            response = self.client.post(
                f"/api/travel-requests/{request.pk}/expenses/",
                data={
                    "category": "OTHER",
                    "expense_date": "2026-12-02",
                    "amount": "1.00",
                    "currency": code,
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=_auth(self.employee),
            )
            self.assertEqual(response.status_code, 201, code)

    def test_reviewer_verifies_and_rejects_expenses(self):
        request = self._create_request(status="EXPENSE_SUBMISSION")

        first = Expense.objects.create(
            travel_request=request,
            category=Expense.Category.FOOD,
            expense_date=date(2026, 12, 2),
            amount="10.00",
            submitted_by=self.employee,
        )

        second = Expense.objects.create(
            travel_request=request,
            category=Expense.Category.OTHER,
            expense_date=date(2026, 12, 3),
            amount="20.00",
            submitted_by=self.employee,
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/expenses/{first.pk}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "VERIFIED")

        ##Rejection requires comments.
        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/expenses/{second.pk}/verify/",
            {"status": "REJECTED"},
        )
        self.assertEqual(response.status_code, 400)

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/expenses/{second.pk}/verify/",
            {"status": "REJECTED", "review_comments": "No receipt"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "REJECTED")

    def test_expense_configuration_reviewer_only(self):
        request = self._create_request(status="MANAGER_APPROVED")

        payload = {
            "max_approved_expenses": "5000.00",
            "advance_amount": "1000.00",
            "currency": "INR",
            "daily_allowance": "200.00",
        }

        ##Employee cannot configure limits.
        response = self.client.put(
            f"/api/travel-requests/{request.pk}/expense-configuration/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(response.status_code, 403)

        ##Manager cannot configure limits (reviewer-only).
        response = self.client.put(
            f"/api/travel-requests/{request.pk}/expense-configuration/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.manager),
        )
        self.assertEqual(response.status_code, 403)

        ##Reviewer configures the limits.
        response = self.client.put(
            f"/api/travel-requests/{request.pk}/expense-configuration/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["max_approved_expenses"], "5000.00")

        ##Employee can view the configured limits.
        response = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/expense-configuration/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["advance_amount"], "1000.00")


class ScenarioGTests(CorrectionTestBase):
    """G. Settlement gating."""

    def _make_verified_expense(self, request):
        return Expense.objects.create(
            travel_request=request,
            category=Expense.Category.FOOD,
            expense_date=date(2026, 12, 2),
            amount="100.00",
            submitted_by=self.employee,
            status=Expense.Status.VERIFIED,
        )

    def test_settlement_calculates_only_at_expense_verification(self):
        request = self._create_request(status="EXPENSE_VERIFICATION")
        self._make_verified_expense(request)

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["eligible_expenses_total"], "100.00"
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "SETTLEMENT_PENDING")

    def test_settlement_cannot_be_calculated_twice(self):
        request = self._create_request(status="EXPENSE_VERIFICATION")
        self._make_verified_expense(request)

        first = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )
        self.assertEqual(first.status_code, 200)

        ##Second attempt is refused even though the request
        ##is now SETTLEMENT_PENDING (not EXPENSE_VERIFICATION).
        second = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )
        self.assertEqual(second.status_code, 400)
        self.assertIn("already", second.data["detail"])

        ##Only one settlement record exists.
        self.assertEqual(Settlement.objects.count(), 1)

    def test_settlement_processing_cannot_calculate_again(self):
        ##The exact user-reported bug: Calculate Settlement
        ##clicked while the request is SETTLEMENT_PROCESSING.
        request = self._create_request(status="EXPENSE_VERIFICATION")
        self._make_verified_expense(request)

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )
        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/start-approval/",
        )
        self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/settlement/approve/",
        )
        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/start-processing/",
        )

        request.refresh_from_db()
        self.assertEqual(request.status, "SETTLEMENT_PROCESSING")

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Settlement.objects.count(), 1)

    def test_settlement_transitions_in_order(self):
        request = self._create_request(status="EXPENSE_VERIFICATION")
        self._make_verified_expense(request)

        base = f"/api/travel-requests/{request.pk}"

        ##Approval before calculation fails cleanly.
        response = self._post(self.manager, f"{base}/settlement/approve/")
        self.assertEqual(response.status_code, 400)

        self._post(self.reviewer, f"{base}/settlement/calculate/")
        self._post(self.reviewer, f"{base}/settlement/start-approval/")

        request.refresh_from_db()
        self.assertEqual(request.status, "SETTLEMENT_APPROVAL")

        ##Reviewer cannot approve the settlement.
        response = self._post(self.reviewer, f"{base}/settlement/approve/")
        self.assertEqual(response.status_code, 403)

        response = self._post(self.manager, f"{base}/settlement/approve/")
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "SETTLEMENT_APPROVED")


class ScenarioHTests(CorrectionTestBase):
    """H. Workflow progress and guidance."""

    def test_progress_reports_stage_completed_and_guidance(self):
        request = self._create_request(status="DOCUMENTS_UNDER_REVIEW")

        response = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/workflow/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["current_stage"], "DOCUMENTS_UNDER_REVIEW"
        )
        self.assertIn(
            "DOCUMENTS_PENDING", response.data["completed_stages"]
        )
        self.assertIn(
            "Reviewer/HR", response.data["pending_with"]
        )
        self.assertIn(
            "verify", response.data["next_action"].lower()
        )

    def test_pending_with_per_stage(self):
        expectations = {
            "MANAGER_APPROVAL": "Manager",
            "VISA_PROCESSING": "Employee",
            "TRAVEL_BOOKING": "Reviewer/HR",
            "EXPENSE_VERIFICATION": "Reviewer/HR",
        }

        for status_value, pending_with in expectations.items():
            request = self._create_request(status=status_value)

            response = self._get(
                self.employee,
                f"/api/travel-requests/{request.pk}/workflow/",
            )

            self.assertEqual(
                response.data["pending_with"],
                pending_with,
                status_value,
            )

    def test_allowed_actions_are_role_filtered(self):
        request = self._create_request(status="MANAGER_APPROVAL")

        reviewer_view = self._get(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/workflow/",
        )
        manager_view = self._get(
            self.manager,
            f"/api/travel-requests/{request.pk}/workflow/",
        )
        employee_view = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/workflow/",
        )

        ##The manager sees approve in their own action list.
        self.assertIn(
            "approve", manager_view.data["my_allowed_actions"]
        )

        ##The reviewer does not (approve is manager-only).
        self.assertNotIn(
            "approve", reviewer_view.data["my_allowed_actions"]
        )

        ##The employee sees neither.
        self.assertNotIn(
            "approve", employee_view.data["my_allowed_actions"]
        )
        self.assertNotIn(
            "start_review",
            employee_view.data["my_allowed_actions"],
        )


class ScenarioITests(CorrectionTestBase):
    """I. Domestic has no visa or international documents."""

    def test_domestic_skips_documents_and_visa(self):
        request = self._create_request(
            travel_type="DOMESTIC",
            country=self.germany,
            status="SUBMITTED",
        )

        ##No document requirements exist for this
        ##domestic trip; the reviewer hands off directly.
        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/submit-for-approval/",
        )
        self.assertEqual(
            response.data["status"], "MANAGER_APPROVAL"
        )

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/approve/",
        )
        self.assertEqual(response.status_code, 200)

        ##Visa endpoints reject domestic requests.
        response = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/",
        )
        self.assertEqual(response.status_code, 400)

        ##And the workflow never contains visa stages.
        response = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/workflow/",
        )
        self.assertNotIn(
            "VISA_PROCESSING", response.data["workflow"]
        )
        self.assertNotIn(
            "DOCUMENTS_UNDER_REVIEW", response.data["workflow"]
        )

    def test_domestic_booking_available_after_approval(self):
        request = self._create_request(
            travel_type="DOMESTIC",
            country=self.germany,
            status="MANAGER_APPROVED",
        )

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/bookings/hotels/",
            data={
                "hotel_name": "Domestic Hotel",
                "check_in": "2026-12-01",
                "check_out": "2026-12-05",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(response.status_code, 201)


class ScenarioJTests(CorrectionTestBase):
    """J. International full flow."""

    def test_international_full_flow(self):
        request = self._create_request(status="DRAFT")
        base = f"/api/travel-requests/{request.pk}"

        self._post(self.employee, f"{base}/submit/")

        self._post(self.reviewer, f"{base}/start-review/")
        upload = self._upload_document(request, self.passport)
        self._verify_document(upload.data["id"])

        ##Documents -> manager approval (auto).
        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVAL")

        ##Manager approves.
        self._post(self.manager, f"{base}/approve/")

        ##Reviewer starts visa; employee updates it.
        self._post(self.reviewer, f"{base}/start-visa/")
        self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "APPLIED"},
        )
        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "APPROVED"},
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "VISA_APPROVED")

        ##Reviewer opens booking and records bookings.
        self._post(self.reviewer, f"{base}/start-booking/")

        self.client.post(
            f"{base}/bookings/flights/",
            data={
                "airline": "Air France",
                "flight_number": "AF109",
                "origin": "Chennai",
                "destination": "Paris",
                "departure_datetime": "2026-12-01T09:00:00",
                "arrival_datetime": "2026-12-01T14:30:00",
                "booking_reference": "AF-J-1",
                "notes": "Aisle seat",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.client.post(
            f"{base}/bookings/hotels/",
            data={
                "hotel_name": "Hotel Lumiere",
                "address": "12 Rue de la Paix, Paris",
                "check_in": "2026-12-01",
                "check_out": "2026-12-05",
                "booking_reference": "HB-J-1",
                "notes": "City view",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        response = self._post(self.reviewer, f"{base}/complete-booking/")
        self.assertEqual(response.data["status"], "TRAVEL_BOOKED")

        ##Travel, expenses, verification.
        self._post(self.employee, f"{base}/start-travel/")
        self._post(self.employee, f"{base}/submit-expenses/")

        expense = self.client.post(
            f"{base}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-12-02",
                "amount": "40.00",
                "currency": "EUR",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(expense.status_code, 201)

        self._post(self.reviewer, f"{base}/start-expense-review/")
        self._post(
            self.reviewer,
            f"{base}/expenses/{expense.data['id']}/verify/",
            {"status": "VERIFIED"},
        )

        ##Settlement lifecycle.
        response = self._post(
            self.reviewer,
            f"{base}/settlement/calculate/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["eligible_expenses_total"], "40.00"
        )

        ##Immediate recalculation is refused.
        response = self._post(
            self.reviewer,
            f"{base}/settlement/calculate/",
        )
        self.assertEqual(response.status_code, 400)

        self._post(self.reviewer, f"{base}/settlement/start-approval/")
        self._post(self.manager, f"{base}/settlement/approve/")
        self._post(self.reviewer, f"{base}/settlement/start-processing/")
        self._post(self.reviewer, f"{base}/complete/")

        response = self._post(self.employee, f"{base}/close/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "CLOSED")


class EmployeeNameTests(CorrectionTestBase):
    """Employee name is a real name, never a bare id."""

    def test_employee_name_in_list_and_detail(self):
        request = self._create_request(status="DRAFT")

        response = self._get(self.employee, "/api/travel-requests/")

        self.assertEqual(response.status_code, 200)

        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )

        match = next(
            (
                item
                for item in results
                if item["id"] == request.pk
            ),
            None,
        )

        self.assertIsNotNone(match)
        self.assertEqual(match["employee_name"], "Corrinne Employee")

        detail = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/",
        )
        self.assertEqual(
            detail.data["employee_name"], "Corrinne Employee"
        )

    def test_username_fallback_when_no_full_name(self):
        request = TravelRequest.objects.create(
            employee=self.other_employee,
            destination_country=self.france,
            destination_city="Paris",
            travel_type="INTERNATIONAL",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            purpose="name fallback",
            status="DRAFT",
        )

        response = self._get(
            self.other_employee,
            f"/api/travel-requests/{request.pk}/",
        )

        self.assertEqual(
            response.data["employee_name"], "corr_other_employee"
        )
