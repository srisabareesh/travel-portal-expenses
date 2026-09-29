"""
Phase 19: end-to-end scenario tests.

SCENARIO A (domestic) and SCENARIO B (international) from the
master specification, driven through the public API, plus the
required negative cases.
"""

from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from rest_framework_simplejwt.tokens import RefreshToken

from documents.models import (
    DocumentRequirement,
    DocumentType,
    EmployeeDocument,
)
from expenses.models import (
    Expense,
    ExpenseConfiguration,
)
from travel.models import Country, TravelRequest
from users.models import User
from users.services import ensure_roles_seeded
from visa.models import Visa


def _auth(user):
    return (
        "Bearer "
        + str(RefreshToken.for_user(user).access_token)
    )


class E2ETestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        ensure_roles_seeded()

        cls.france = Country.objects.create(
            name="France",
            country_code="FR",
        )

        cls.germany = Country.objects.create(
            name="Germany",
            country_code="DE",
        )

        cls.employee = User.objects.create_user(
            username="e2e_employee",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        cls.manager = User.objects.create_user(
            username="e2e_manager",
            password="TestPassword123",
            role="MANAGER",
        )

        cls.reviewer = User.objects.create_user(
            username="e2e_reviewer",
            password="TestPassword123",
            role="REVIEWER",
        )

        cls.admin = User.objects.create_user(
            username="e2e_admin",
            password="TestPassword123",
            role="ADMIN",
        )

        cls.employee.manager = cls.manager
        cls.employee.save()

        cls.passport = DocumentType.objects.create(
            name="E2E Passport",
        )

        cls.invitation = DocumentType.objects.create(
            name="E2E Invitation Letter",
        )

        DocumentRequirement.objects.create(
            country=cls.france,
            document_type=cls.passport,
            travel_type="INTERNATIONAL",
            mandatory=True,
        )

        DocumentRequirement.objects.create(
            country=cls.france,
            document_type=cls.invitation,
            travel_type="INTERNATIONAL",
            mandatory=True,
        )

    def _create_request(
        self,
        travel_type="DOMESTIC",
        country=None,
    ):
        payload = {
            "destination_country": (
                country or self.germany
            ).id,
            "destination_city": "Berlin",
            "client": "Client E2E",
            "project": "Project E2E",
            "travel_type": travel_type,
            "start_date": "2026-12-01",
            "end_date": "2026-12-05",
            "purpose": "E2E scenario",
        }

        response = self.client.post(
            "/api/travel-requests/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        assert response.status_code == 201, response.data

        return response.data["id"]

    def _post(self, user, url, data=None):
        return self.client.post(
            url,
            data=data or {},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(user),
        )

    def _status(self, travel_request_id):
        response = self.client.get(
            f"/api/travel-requests/{travel_request_id}/",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        return response.data["status"]


class DomesticE2EScenarioTests(E2ETestBase):
    """SCENARIO A: domestic happy path through the API."""

    def test_domestic_full_lifecycle(self):
        request_id = self._create_request(
            travel_type="DOMESTIC"
        )

        base = f"/api/travel-requests/{request_id}"

        ##1-4. Employee created the request (draft).
        self.assertEqual(
            self._status(request_id),
            "DRAFT",
        )

        ##5. Employee submits.
        response = self._post(
            self.employee,
            f"{base}/submit/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], "SUBMITTED"
        )

        ##6-7. Manager approves (domestic: no document
        ##stage; reviewer hands off for approval).
        response = self._post(
            self.reviewer,
            f"{base}/submit-for-approval/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVAL",
        )

        response = self._post(
            self.manager,
            f"{base}/approve/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVED",
        )

        ##8-9. Booking created and completed.
        response = self._post(
            self.reviewer,
            f"{base}/start-booking/",
        )
        self.assertEqual(
            response.data["status"], "TRAVEL_BOOKING"
        )

        flight_response = self.client.post(
            f"{base}/bookings/flights/",
            data={
                "airline": "Lufthansa",
                "flight_number": "LH1024",
                "booking_reference": "PNR-E2E-1",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(flight_response.status_code, 201)

        hotel_response = self.client.post(
            f"{base}/bookings/hotels/",
            data={
                "hotel_name": "Hotel Berlin",
                "booking_reference": "HB-E2E-1",
                "check_in": "2026-12-01",
                "check_out": "2026-12-05",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(hotel_response.status_code, 201)

        response = self._post(
            self.reviewer,
            f"{base}/complete-booking/",
        )
        self.assertEqual(
            response.data["status"], "TRAVEL_BOOKED"
        )

        ##10. Travel starts.
        response = self._post(
            self.employee,
            f"{base}/start-travel/",
        )
        self.assertEqual(
            response.data["status"],
            "TRAVEL_IN_PROGRESS",
        )

        ##11. Employee submits expenses.
        response = self._post(
            self.employee,
            f"{base}/submit-expenses/",
        )
        self.assertEqual(
            response.data["status"],
            "EXPENSE_SUBMISSION",
        )

        ##Reviewer picks the request up for expense
        ##verification (EXPENSE_SUBMISSION ->
        ##EXPENSE_VERIFICATION).
        response = self._post(
            self.reviewer,
            f"{base}/start-expense-review/",
        )
        self.assertEqual(
            response.data["status"],
            "EXPENSE_VERIFICATION",
        )

        expense_response = self.client.post(
            f"{base}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-12-02",
                "amount": "60.00",
                "currency": "EUR",
                "description": "Meals",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(expense_response.status_code, 201)

        ##12. Reviewer verifies the expense.
        response = self._post(
            self.reviewer,
            f"{base}/expenses/{expense_response.data['id']}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(
            response.data["status"], "VERIFIED"
        )

        ##13. Settlement is calculated.
        response = self._post(
            self.reviewer,
            f"{base}/settlement/calculate/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["eligible_expenses_total"],
            "60.00",
        )
        self.assertEqual(
            self._status(request_id),
            "SETTLEMENT_PENDING",
        )

        ##14-15. Manager approves the settlement and
        ##finance processes it.
        self._post(
            self.reviewer,
            f"{base}/settlement/start-approval/",
        )

        response = self._post(
            self.manager,
            f"{base}/settlement/approve/",
        )
        self.assertEqual(response.status_code, 200)

        response = self._post(
            self.reviewer,
            f"{base}/settlement/start-processing/",
            {
                "payment_date": "2026-12-20",
                "payment_reference": "PAY-1",
                "payment_method": "Bank transfer",
            },
        )
        self.assertEqual(response.status_code, 200)

        ##16. Completed.
        response = self._post(
            self.reviewer,
            f"{base}/complete/",
        )
        self.assertEqual(
            response.data["status"], "COMPLETED"
        )

        ##17. Closed.
        response = self._post(
            self.employee,
            f"{base}/close/",
        )
        self.assertEqual(
            response.data["status"], "CLOSED"
        )

        travel_request = TravelRequest.objects.get(
            pk=request_id
        )

        self.assertEqual(
            travel_request.status, "CLOSED"
        )

        ##Completed requests cannot go back.
        response = self._post(
            self.employee,
            f"{base}/submit/",
        )
        self.assertEqual(response.status_code, 400)


class InternationalE2EScenarioTests(E2ETestBase):
    """SCENARIO B: international lifecycle including
    document rejection, re-upload and visa."""

    def _upload_document(self, request_id, document_type, filename):
        return self.client.post(
            f"/api/travel-requests/{request_id}/documents/upload/",
            data={
                "document_type": document_type.id,
                "file": SimpleUploadedFile(
                    filename,
                    b"%PDF-1.4 fake pdf",
                    content_type="application/pdf",
                ),
            },
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

    def _verify_document(
        self,
        request_id,
        document_id,
        decision,
        comments="",
    ):
        return self._post(
            self.reviewer,
            f"/api/documents/{document_id}/verify/",
            {
                "status": decision,
                "comments": comments,
            },
        )

    def test_international_full_lifecycle(self):
        request_id = self._create_request(
            travel_type="INTERNATIONAL",
            country=self.france,
        )

        base = f"/api/travel-requests/{request_id}"

        ##4. Employee submits.
        response = self._post(
            self.employee,
            f"{base}/submit/",
        )
        self.assertEqual(response.status_code, 200)

        ##5. Documents are generated (checklist has the
        ##two mandatory French requirements).
        checklist_response = self.client.get(
            f"{base}/documents/",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(
            len(checklist_response.data), 2
        )

        ##Request entered the new workflow: the reviewer
        ##starts document review.
        response = self._post(
            self.reviewer,
            f"{base}/start-review/",
        )
        self.assertEqual(
            response.data["status"],
            "DOCUMENTS_PENDING",
        )

        ##6. Employee uploads the passport.
        upload = self._upload_document(
            request_id,
            self.passport,
            "passport.pdf",
        )
        self.assertEqual(upload.status_code, 201)

        passport_doc_id = upload.data["id"]

        ##7. Reviewer rejects the passport (comments
        ##mandatory).
        rejection = self._verify_document(
            request_id,
            passport_doc_id,
            "REJECTED",
            comments="Blurry scan",
        )
        self.assertEqual(rejection.status_code, 201)

        ##8-9. Employee re-uploads a corrected version;
        ##the old version remains in history.
        reupload = self._upload_document(
            request_id,
            self.passport,
            "passport-v2.pdf",
        )
        self.assertEqual(reupload.status_code, 201)

        versions = EmployeeDocument.objects.filter(
            travel_request_id=request_id,
            document_type=self.passport,
        ).order_by("id")

        self.assertEqual(versions.count(), 2)

        self.assertEqual(
            versions.first().status, "REJECTED"
        )

        ##10. Reviewer approves the re-uploaded version.
        response = self._verify_document(
            request_id,
            reupload.data["id"],
            "APPROVED",
        )
        self.assertEqual(response.status_code, 201)

        ##11. Upload and verify the invitation letter.
        invitation_upload = self._upload_document(
            request_id,
            self.invitation,
            "invitation.pdf",
        )
        self.assertEqual(invitation_upload.status_code, 201)

        response = self._verify_document(
            request_id,
            invitation_upload.data["id"],
            "APPROVED",
        )
        self.assertEqual(response.status_code, 201)

        ##12-13. All mandatory documents verified: manager
        ##approval becomes available.
        response = self._post(
            self.reviewer,
            f"{base}/submit-for-approval/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVAL",
        )

        response = self._post(
            self.manager,
            f"{base}/approve/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVED",
        )

        ##14-15. Visa processing and approval.
        response = self._post(
            self.reviewer,
            f"{base}/start-visa/",
        )
        self.assertEqual(
            response.data["status"], "VISA_PROCESSING"
        )

        ##The visa record materializes with the first
        ##state change (UNDER_PROCESS via the visa API).
        self._post(
            self.reviewer,
            f"/api/travel-requests/{request_id}/visa/decision/",
            {"state": "UNDER_PROCESS"},
        )

        response = self._post(
            self.reviewer,
            f"{base}/visa-decide/",
            {"decision": "APPROVED"},
        )
        self.assertEqual(
            response.data["status"], "VISA_APPROVED"
        )

        ##16-17. Booking.
        self._post(self.reviewer, f"{base}/start-booking/")

        self.client.post(
            f"{base}/bookings/flights/",
            data={
                "airline": "Air France",
                "booking_reference": "PNR-E2E-2",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        response = self._post(
            self.reviewer,
            f"{base}/complete-booking/",
        )
        self.assertEqual(
            response.data["status"], "TRAVEL_BOOKED"
        )

        ##18-19. Travel and expenses.
        self._post(self.employee, f"{base}/start-travel/")

        self._post(
            self.employee,
            f"{base}/submit-expenses/",
        )

        response = self._post(
            self.reviewer,
            f"{base}/start-expense-review/",
        )
        self.assertEqual(
            response.data["status"],
            "EXPENSE_VERIFICATION",
        )

        expense = self.client.post(
            f"{base}/expenses/",
            data={
                "category": "VISA",
                "expense_date": "2026-12-03",
                "amount": "99.00",
                "currency": "EUR",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )
        self.assertEqual(expense.status_code, 201)

        ##20. Verification.
        self._post(
            self.reviewer,
            f"{base}/expenses/{expense.data['id']}/verify/",
            {"status": "VERIFIED"},
        )

        ##21-23. Settlement calculation, approval and
        ##processing.
        response = self._post(
            self.reviewer,
            f"{base}/settlement/calculate/",
        )
        self.assertEqual(
            response.data["eligible_expenses_total"],
            "99.00",
        )

        self._post(
            self.reviewer,
            f"{base}/settlement/start-approval/",
        )
        self._post(
            self.manager,
            f"{base}/settlement/approve/",
        )
        response = self._post(
            self.reviewer,
            f"{base}/settlement/start-processing/",
        )
        self.assertEqual(response.status_code, 200)

        ##24-25. Completed and closed.
        self._post(self.reviewer, f"{base}/complete/")

        response = self._post(
            self.employee,
            f"{base}/close/",
        )
        self.assertEqual(
            response.data["status"], "CLOSED"
        )

        ##Audit trail exists for the journey.
        from audit.models import AuditLog

        self.assertTrue(
            AuditLog.objects.filter(
                travel_request_id=request_id
            ).exists()
        )

        ##Notifications were generated for the employee.
        from notifications.models import Notification

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.employee,
                travel_request_id=request_id,
            ).exists()
        )


class NegativeE2ETests(E2ETestBase):
    """Required negative scenarios."""

    def _make_request(self, status, travel_type="DOMESTIC"):
        return TravelRequest.objects.create(
            employee=self.employee,
            destination_country=self.germany,
            destination_city="Berlin",
            travel_type=travel_type,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            purpose="negative test",
            status=status,
        )

    def test_employee_cannot_approve(self):
        request = self._make_request("MANAGER_APPROVAL")

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_approve_without_manager_role(self):
        request = self._make_request("MANAGER_APPROVAL")

        response = self._post(
            self.admin,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_with_explicit_manager_role_can_approve_team(self):
        ##Rule 15: ADMIN gets business authority only via
        ##explicit role assignment.
        from users.services import assign_role
        from users.models import Role

        assign_role(self.admin, Role.Name.MANAGER)

        self.employee.manager = self.admin
        self.employee.save()

        request = self._make_request("MANAGER_APPROVAL")

        response = self._post(
            self.admin,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVED",
        )

    def test_manager_cannot_approve_own_request(self):
        request = TravelRequest.objects.create(
            employee=self.manager,
            destination_country=self.germany,
            destination_city="Berlin",
            travel_type="DOMESTIC",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            purpose="own request",
            status="MANAGER_APPROVAL",
        )

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_approve_other_team(self):
        other_employee = User.objects.create_user(
            username="e2e_other_emp",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        request = self._make_request("MANAGER_APPROVAL")

        request.employee = other_employee
        request.save()

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_international_cannot_skip_documents(self):
        ##An INTERNATIONAL request at SUBMITTED must not
        ##be sendable straight to manager approval while
        ##mandatory documents are missing.
        request = self._make_request(
            "SUBMITTED",
            travel_type="INTERNATIONAL",
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/submit-for-approval/",
        )

        self.assertEqual(response.status_code, 400)

    def test_domestic_cannot_enter_document_or_visa_stages(self):
        request = self._make_request("SUBMITTED")

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )
        self.assertEqual(response.status_code, 400)

        request.status = "MANAGER_APPROVED"
        request.save()

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-visa/",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.get(
            f"/api/travel-requests/{request.pk}/visa/",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )
        self.assertEqual(response.status_code, 400)

    def test_visa_rejection_blocks_booking(self):
        request = self._make_request(
            "VISA_PROCESSING",
            travel_type="INTERNATIONAL",
        )

        Visa.objects.create(
            travel_request=request,
            state=Visa.State.APPLIED,
        )

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "REJECTED"},
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-booking/",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejected_expense_not_counted_in_settlement(self):
        request = self._make_request(
            "EXPENSE_VERIFICATION"
        )

        Expense.objects.create(
            travel_request=request,
            category=Expense.Category.FOOD,
            expense_date=date(2026, 12, 2),
            amount="100.00",
            submitted_by=self.employee,
            status=Expense.Status.REJECTED,
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["eligible_expenses_total"],
            "0.00",
        )

        self.assertEqual(
            response.data["rejected_expenses_total"],
            "100.00",
        )

    def test_settlement_cannot_be_approved_before_calculation(self):
        request = self._make_request("EXPENSE_VERIFICATION")

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/settlement/approve/",
        )

        self.assertEqual(response.status_code, 400)

    def test_direct_status_patch_is_rejected(self):
        request = self._make_request("DRAFT")

        response = self.client.patch(
            f"/api/travel-requests/{request.pk}/",
            data={"status": "COMPLETED"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()

        self.assertEqual(request.status, "DRAFT")

    def test_invalid_date_pair_is_rejected(self):
        response = self.client.post(
            "/api/travel-requests/",
            data={
                "destination_country": self.germany.id,
                "destination_city": "Berlin",
                "travel_type": "DOMESTIC",
                "start_date": "2026-12-10",
                "end_date": "2026-12-01",
                "purpose": "bad dates",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 400)

    def test_historical_legacy_record_remains_readable(self):
        request = TravelRequest.objects.create(
            employee=self.employee,
            destination_country=self.germany,
            destination_city="Berlin",
            travel_type="BUSINESS",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 5),
            purpose="historical",
            status="DOCUMENT_VERIFICATION",
        )

        response = self.client.get(
            f"/api/travel-requests/{request.pk}/",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["travel_type"], "BUSINESS"
        )

        self.assertTrue(
            response.data["travel_type_is_legacy"]
        )
