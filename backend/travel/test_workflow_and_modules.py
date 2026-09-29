"""
Phase 3.4-3.11 + Phase 4/6/7-12 integration tests.

Covers:
    * Date validation (create, full update, partial PATCH)
    * Central workflow engine rules
    * Workflow transition API (roles, ownership, prerequisites)
    * Domestic and international happy paths
    * Visa module rules
    * Booking module rules
    * Expense configuration / submission / verification
    * Settlement calculation, approval, processing
    * Notifications and audit logging
    * Negative scenarios (status manipulation, skips, self-approval)
"""

from datetime import date

from django.test import TestCase

from rest_framework_simplejwt.tokens import RefreshToken

from documents.models import DocumentType, DocumentRequirement
from expenses.models import (
    Expense,
    ExpenseConfiguration,
    Settlement,
)
from travel.models import Country, TravelRequest
from users.models import User, Role
from users.services import ensure_roles_seeded


def _auth(user):
    return (
        "Bearer "
        + str(RefreshToken.for_user(user).access_token)
    )


class WorkflowTestBase(TestCase):
    """Shared fixture builder for workflow tests."""

    @classmethod
    def setUpTestData(cls):

        ensure_roles_seeded()

        cls.country = Country.objects.create(
            name="France",
            country_code="FR",
        )

        cls.employee = User.objects.create_user(
            username="wf_employee",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        cls.manager = User.objects.create_user(
            username="wf_manager",
            password="TestPassword123",
            role="MANAGER",
        )

        cls.reviewer = User.objects.create_user(
            username="wf_reviewer",
            password="TestPassword123",
            role="REVIEWER",
        )

        cls.admin = User.objects.create_user(
            username="wf_admin",
            password="TestPassword123",
            role="ADMIN",
        )

        cls.employee.manager = cls.manager
        cls.employee.save()

    def _create_request(
        self,
        travel_type="DOMESTIC",
        employee=None,
        status="DRAFT",
    ):
        return TravelRequest.objects.create(
            employee=employee or self.employee,
            destination_country=self.country,
            destination_city="Paris",
            client="Client A",
            project="Project A",
            travel_type=travel_type,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 5),
            purpose="Workflow test",
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


class DateValidationTests(WorkflowTestBase):
    """Phase 3.4: effective date-pair validation."""

    def _payload(self, **overrides):
        payload = {
            "destination_country": self.country.id,
            "destination_city": "Paris",
            "client": "C",
            "project": "P",
            "travel_type": "DOMESTIC",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "purpose": "Dates",
        }

        payload.update(overrides)

        return payload

    def test_create_rejects_inverted_dates(self):
        response = self.client.post(
            "/api/travel-requests/",
            data=self._payload(
                end_date="2026-10-01",
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

    def test_create_accepts_equal_dates(self):
        response = self.client.post(
            "/api/travel-requests/",
            data=self._payload(
                end_date="2026-11-01",
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 201)

    def test_patch_single_earlier_end_date_fails(self):
        travel_request = self._create_request()

        response = self.client.patch(
            f"/api/travel-requests/{travel_request.pk}/",
            data={"end_date": "2026-10-01"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 400)

        travel_request.refresh_from_db()

        self.assertEqual(
            str(travel_request.end_date),
            "2026-11-05",
        )

    def test_patch_single_later_start_date_fails(self):
        travel_request = self._create_request()

        response = self.client.patch(
            f"/api/travel-requests/{travel_request.pk}/",
            data={"start_date": "2026-12-01"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 400)

    def test_patch_single_coherent_date_succeeds(self):
        travel_request = self._create_request()

        response = self.client.patch(
            f"/api/travel-requests/{travel_request.pk}/",
            data={"end_date": "2026-11-10"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 200)

        travel_request.refresh_from_db()

        self.assertEqual(
            str(travel_request.end_date),
            "2026-11-10",
        )

    def test_patch_without_dates_skips_date_validation(self):
        ##A historical record whose stored pair is
        ##incoherent (only possible via admin) must stay
        ##editable in other fields.
        travel_request = self._create_request()
        travel_request.end_date = date(2026, 1, 1)
        travel_request.save()

        response = self.client.patch(
            f"/api/travel-requests/{travel_request.pk}/",
            data={"purpose": "Edited without dates"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 200)


class WorkflowEngineTests(WorkflowTestBase):
    """Phase 3.6: central engine rules."""

    def test_legacy_travel_type_has_no_workflow(self):
        travel_request = self._create_request(
            travel_type="BUSINESS"
        )

        with self.assertRaises(Exception):
            from travel.services import get_workflow

            get_workflow(travel_request)

    def test_invalid_transition_is_rejected(self):
        from travel.services import (
            WorkflowError,
            validate_transition,
        )

        travel_request = self._create_request()

        ##DRAFT -> COMPLETED is impossible: complete only
        ##applies to SETTLEMENT_PROCESSING.
        with self.assertRaises(WorkflowError):
            validate_transition(
                travel_request,
                "complete",
            )

    def test_unknown_action_is_rejected(self):
        from travel.services import (
            WorkflowError,
            validate_transition,
        )

        travel_request = self._create_request()

        with self.assertRaises(WorkflowError):
            validate_transition(
                travel_request,
                "self_destruct",
            )


class WorkflowTransitionApiTests(WorkflowTestBase):
    """Phase 3.7/3.8/3.9: secure transition endpoints."""

    def test_employee_cannot_set_status_directly(self):
        travel_request = self._create_request()

        response = self.client.patch(
            f"/api/travel-requests/{travel_request.pk}/",
            data={"status": "COMPLETED"},
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 200)

        travel_request.refresh_from_db()

        ##Status is read-only in the serializer.
        self.assertEqual(
            travel_request.status,
            "DRAFT",
        )

    def test_domestic_happy_path_full_lifecycle(self):
        travel_request = self._create_request()
        base = f"/api/travel-requests/{travel_request.pk}"

        ##Employee submits.
        response = self._post(
            self.employee,
            f"{base}/submit/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], "SUBMITTED"
        )

        ##Domestic: no document stage. The reviewer (or
        ##an auto-hand-off) submits straight for manager
        ##approval from SUBMITTED.
        response = self._post(
            self.reviewer,
            f"{base}/submit-for-approval/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVAL",
        )

        ##Manager approves.
        response = self._post(
            self.manager,
            f"{base}/approve/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVED",
        )

        ##Booking, travel, expenses, verification,
        ##settlement, completion, closure.
        self._post(self.reviewer, f"{base}/start-booking/")
        self._post(
            self.reviewer,
            f"{base}/complete-booking/",
        )
        self._post(self.employee, f"{base}/start-travel/")
        self._post(
            self.employee,
            f"{base}/submit-expenses/",
        )
        self._post(
            self.reviewer,
            f"{base}/start-expense-review/",
        )
        self._post(self.reviewer, f"{base}/settle/")
        self._post(
            self.reviewer,
            f"{base}/start-settlement-approval/",
        )
        response = self._post(
            self.manager,
            f"{base}/approve-settlement/",
        )
        self.assertEqual(response.status_code, 200)
        self._post(
            self.reviewer,
            f"{base}/start-settlement-processing/",
        )
        response = self._post(
            self.reviewer,
            f"{base}/complete/",
        )
        self.assertEqual(
            response.data["status"],
            "COMPLETED",
        )

        response = self._post(
            self.employee,
            f"{base}/close/",
        )
        self.assertEqual(
            response.data["status"],
            "CLOSED",
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.status,
            "CLOSED",
        )

    def test_international_path_with_documents_and_visa(self):
        travel_request = self._create_request(
            travel_type="INTERNATIONAL"
        )
        base = f"/api/travel-requests/{travel_request.pk}"

        self._post(self.employee, f"{base}/submit/")
        self._post(self.reviewer, f"{base}/start-review/")

        response = self._post(
            self.reviewer,
            f"{base}/submit-for-approval/",
        )
        self.assertEqual(
            response.data["status"],
            "MANAGER_APPROVAL",
        )

        self._post(self.manager, f"{base}/approve/")

        ##Visa flow.
        response = self._post(
            self.reviewer,
            f"{base}/start-visa/",
        )
        self.assertEqual(
            response.data["status"],
            "VISA_PROCESSING",
        )

        response = self._post(
            self.reviewer,
            f"{base}/visa-decide/",
            {"decision": "APPROVED"},
        )
        self.assertEqual(
            response.data["status"],
            "VISA_APPROVED",
        )

        ##Booking continues from VISA_APPROVED.
        response = self._post(
            self.reviewer,
            f"{base}/start-booking/",
        )
        self.assertEqual(
            response.data["status"],
            "TRAVEL_BOOKING",
        )

    def test_employee_cannot_approve(self):
        travel_request = self._create_request(
            status="MANAGER_APPROVAL"
        )

        response = self._post(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_without_manager_role_cannot_approve(self):
        travel_request = self._create_request(
            status="MANAGER_APPROVAL"
        )

        response = self._post(
            self.admin,
            f"/api/travel-requests/{travel_request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_approve_other_team(self):
        other_employee = User.objects.create_user(
            username="wf_other_emp",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        travel_request = self._create_request(
            employee=other_employee,
            status="MANAGER_APPROVAL",
        )

        response = self._post(
            self.manager,
            f"/api/travel-requests/{travel_request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_approve_own_request(self):
        travel_request = self._create_request(
            employee=self.manager,
            status="MANAGER_APPROVAL",
        )

        response = self._post(
            self.manager,
            f"/api/travel-requests/{travel_request.pk}/approve/",
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_submit_other_request(self):
        other_employee = User.objects.create_user(
            username="wf_other_emp2",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        travel_request = self._create_request(
            employee=other_employee
        )

        response = self._post(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/submit/",
        )

        self.assertEqual(response.status_code, 403)

    def test_workflow_progress_endpoint(self):
        travel_request = self._create_request()

        response = self._get(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/workflow/",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["travel_type"],
            "DOMESTIC",
        )

        self.assertEqual(
            response.data["current_stage"],
            "DRAFT",
        )

        self.assertIn(
            "submit",
            response.data["allowed_actions"],
        )


class VisaModuleTests(WorkflowTestBase):
    """Phase 4: visa tracking rules."""

    def test_visa_view_rejects_domestic_request(self):
        travel_request = self._create_request(
            travel_type="DOMESTIC"
        )

        response = self._get(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/visa/",
        )

        self.assertEqual(response.status_code, 400)

    def test_visa_flow_apply_and_approve(self):
        travel_request = self._create_request(
            travel_type="INTERNATIONAL"
        )

        ##Employee can view.
        response = self._get(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/visa/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["state"], "NOT_APPLIED"
        )

        ##Employee cannot apply.
        response = self._post(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/visa/apply/",
            {"applied_on": "2026-11-20"},
        )
        self.assertEqual(response.status_code, 403)

        ##Reviewer applies.
        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/visa/apply/",
            {"applied_on": "2026-11-20"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["state"], "APPLIED"
        )

        ##Reviewer approves.
        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/visa/decision/",
            {"state": "APPROVED"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["state"], "APPROVED"
        )

    def test_visa_rejection_does_not_advance_request(self):
        from visa.models import Visa

        travel_request = self._create_request(
            travel_type="INTERNATIONAL",
            status="VISA_PROCESSING",
        )

        visa = Visa.objects.create(
            travel_request=travel_request,
            state=Visa.State.APPLIED,
            applied_on=date(2026, 11, 20),
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/visa/decision/",
            {"state": "REJECTED"},
        )
        self.assertEqual(response.status_code, 200)

        travel_request.refresh_from_db()

        ##Request status unchanged: rejection must not
        ##move the request to booking.
        self.assertEqual(
            travel_request.status,
            "VISA_PROCESSING",
        )


class BookingModuleTests(WorkflowTestBase):
    """Phase 6: flight and hotel bookings."""

    def test_reviewer_can_record_flight_and_hotel(self):
        travel_request = self._create_request(
            status="MANAGER_APPROVED"
        )

        response = self.client.post(
            f"/api/travel-requests/{travel_request.pk}/bookings/flights/",
            data={
                "airline": "Air France",
                "flight_number": "AF123",
                "booking_reference": "PNR-001",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/travel-requests/{travel_request.pk}/bookings/hotels/",
            data={
                "hotel_name": "Hotel Paris",
                "booking_reference": "HB-001",
                "check_in": "2026-11-01",
                "check_out": "2026-11-05",
                "status": "BOOKED",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.reviewer),
        )

        self.assertEqual(response.status_code, 201)

        ##Employee can view bookings.
        response = self._get(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/bookings/hotels/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class ExpenseModuleTests(WorkflowTestBase):
    """Phases 7-12: configuration, expenses, settlement."""

    def test_expense_submission_and_verification(self):
        travel_request = self._create_request(
            status="EXPENSE_SUBMISSION"
        )

        response = self.client.post(
            f"/api/travel-requests/{travel_request.pk}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-11-02",
                "amount": "42.50",
                "currency": "EUR",
                "description": "Dinner",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 201)
        expense_id = response.data["id"]

        ##Employee cannot verify.
        response = self._post(
            self.employee,
            f"/api/travel-requests/{travel_request.pk}/expenses/{expense_id}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(response.status_code, 403)

        ##Reviewer verifies.
        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/expenses/{expense_id}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"], "VERIFIED"
        )

    def test_expense_validation_rejects_bad_amount(self):
        travel_request = self._create_request(
            status="EXPENSE_SUBMISSION"
        )

        response = self.client.post(
            f"/api/travel-requests/{travel_request.pk}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-11-02",
                "amount": "-5",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_submit_for_other(self):
        other_employee = User.objects.create_user(
            username="wf_other_emp3",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        travel_request = self._create_request(
            employee=other_employee,
            status="EXPENSE_SUBMISSION",
        )

        response = self.client.post(
            f"/api/travel-requests/{travel_request.pk}/expenses/",
            data={
                "category": "FOOD",
                "expense_date": "2026-11-02",
                "amount": "10",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(self.employee),
        )

        self.assertEqual(response.status_code, 403)

    def test_settlement_calculation_and_approval(self):
        travel_request = self._create_request(
            status="EXPENSE_VERIFICATION"
        )

        ExpenseConfiguration.objects.create(
            travel_request=travel_request,
            advance_amount="100.00",
            advance_paid=True,
            daily_allowance="10.00",
            currency="EUR",
        )

        Expense.objects.create(
            travel_request=travel_request,
            category=Expense.Category.FOOD,
            expense_date=date(2026, 11, 2),
            amount="50.00",
            submitted_by=self.employee,
            status=Expense.Status.VERIFIED,
        )

        Expense.objects.create(
            travel_request=travel_request,
            category=Expense.Category.OTHER,
            expense_date=date(2026, 11, 3),
            amount="30.00",
            submitted_by=self.employee,
            status=Expense.Status.REJECTED,
        )

        ##Domestic 5-day trip: 50 eligible + 50 allowance
        ##- 100 advance = 0 net.
        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/settlement/calculate/",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["eligible_expenses_total"],
            "50.00",
        )

        self.assertEqual(
            response.data["allowances_total"],
            "50.00",
        )

        self.assertEqual(
            response.data["advance_paid"],
            "100.00",
        )

        self.assertEqual(
            response.data["net_settlement"],
            "0.00",
        )

        travel_request.refresh_from_db()

        self.assertEqual(
            travel_request.status,
            "SETTLEMENT_PENDING",
        )

        ##Approval flow.
        self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/settlement/start-approval/",
        )

        response = self._post(
            self.manager,
            f"/api/travel-requests/{travel_request.pk}/settlement/approve/",
        )

        self.assertEqual(response.status_code, 200)

        settlement = Settlement.objects.get(
            travel_request=travel_request
        )

        self.assertEqual(
            settlement.status,
            Settlement.Status.APPROVED,
        )

    def test_settlement_requires_verified_expense_stage(self):
        travel_request = self._create_request(
            status="TRAVEL_BOOKED"
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/settlement/calculate/",
        )

        self.assertEqual(response.status_code, 400)

    def test_settlement_approval_requires_manager(self):
        travel_request = self._create_request(
            status="SETTLEMENT_APPROVAL"
        )

        Settlement.objects.create(
            travel_request=travel_request,
        )

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{travel_request.pk}/settlement/approve/",
        )

        self.assertEqual(response.status_code, 403)


class NotificationAuditTests(WorkflowTestBase):
    """Phases 13-14: notifications and audit records."""

    def test_approval_generates_audit_and_notification(self):
        from audit.models import AuditLog
        from notifications.models import Notification

        travel_request = self._create_request(
            status="MANAGER_APPROVAL"
        )

        from travel.services import (
            apply_workflow_transition_with_side_effects,
        )

        apply_workflow_transition_with_side_effects(
            travel_request,
            "approve",
            self.manager,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                travel_request=travel_request,
                action="APPROVE",
            ).exists()
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.employee,
                travel_request=travel_request,
            ).exists()
        )

    def test_audit_service_never_raises(self):
        from audit.services import log_action

        result = log_action(
            None,
            "TEST_ACTION",
            travel_request=None,
        )

        self.assertIsNotNone(result)
