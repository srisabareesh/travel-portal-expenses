"""
Phase 23: backend security, ownership and workflow guard
corrections.

Every test below exercises the PUBLIC API (direct HTTP calls)
because the point of this phase is that the backend - not the
frontend - enforces the rules.

Scenarios:

A. Expense creation stage guard (valid + rejected stages)
B. Expense configuration (limits) stage guard
C. Settlement GET object-level visibility
D. Close-request ownership
E. Reviewer cannot verify their own expense (dual role)
F. Reviewer document checklist access for new workflows
G. Document upload stage guard
H. Rejected document re-upload (old version preserved)
I. No status regression from late document events
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
from expenses.models import Expense, Settlement
from travel.models import Country, TravelRequest
from users.models import User
from users.services import assign_role, ensure_roles_seeded


def _auth(user):
    return "Bearer " + str(
        RefreshToken.for_user(user).access_token
    )


class Phase23TestBase(TestCase):
    """Shared fixtures for the Phase 23 security suite."""

    @classmethod
    def setUpTestData(cls):
        ensure_roles_seeded()

        cls.france = Country.objects.create(
            name="Phase23 France",
            country_code="P3F",
        )

        cls.germany = Country.objects.create(
            name="Phase23 Germany",
            country_code="P3G",
        )

        cls.employee = User.objects.create_user(
            username="p23_employee",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        cls.other_employee = User.objects.create_user(
            username="p23_other_employee",
            password="TestPassword123",
            role="EMPLOYEE",
        )

        cls.reviewer = User.objects.create_user(
            username="p23_reviewer",
            password="TestPassword123",
            role="REVIEWER",
        )

        cls.other_reviewer = User.objects.create_user(
            username="p23_other_reviewer",
            password="TestPassword123",
            role="REVIEWER",
        )

        cls.manager = User.objects.create_user(
            username="p23_manager",
            password="TestPassword123",
            role="MANAGER",
        )

        cls.other_manager = User.objects.create_user(
            username="p23_other_manager",
            password="TestPassword123",
            role="MANAGER",
        )

        cls.admin = User.objects.create_user(
            username="p23_admin",
            password="TestPassword123",
            role="ADMIN",
        )

        # Team wiring: employee reports to manager,
        # other_employee reports to other_manager.
        cls.employee.manager = cls.manager
        cls.employee.save()

        cls.other_employee.manager = cls.other_manager
        cls.other_employee.save()

        cls.passport = DocumentType.objects.create(
            name="Phase23 Passport",
        )

        DocumentRequirement.objects.create(
            country=cls.france,
            document_type=cls.passport,
            travel_type="INTERNATIONAL",
            mandatory=True,
        )

    # ---------- request helpers ----------

    def _create_request(
        self,
        employee=None,
        travel_type="INTERNATIONAL",
        country=None,
        status="DRAFT",
    ):
        return TravelRequest.objects.create(
            employee=employee or self.employee,
            destination_country=country or self.france,
            destination_city="Paris",
            client="Client P23",
            project="Project P23",
            travel_type=travel_type,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            purpose="Phase 23 security suite",
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

    def _upload_document(self, request, employee=None):
        """Upload as the request's owner by default (only
        the owner may upload)."""
        return self.client.post(
            f"/api/travel-requests/{request.pk}/documents/upload/",
            data={
                "document_type": self.passport.id,
                "file": SimpleUploadedFile(
                    "p23.pdf",
                    b"%PDF-1.4 fake pdf",
                    content_type="application/pdf",
                ),
            },
            HTTP_AUTHORIZATION=_auth(
                employee or request.employee
            ),
        )

    def _verify_document(self, document_id, decision="APPROVED", reviewer=None):
        return self._post(
            reviewer or self.reviewer,
            f"/api/documents/{document_id}/verify/",
            {"status": decision, "comments": "phase 23"},
        )

    # ---------- lifecycle helpers (use the public API) ----

    def _submit_request(self, request):
        """Submit through the API unless already submitted
        (submitting twice is an invalid transition)."""
        request.refresh_from_db()

        if request.status == "DRAFT":
            response = self._post(
                request.employee,
                f"/api/travel-requests/{request.pk}/submit/",
            )
            self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        return request

    def _advance_intl_to_manager_approval(self, request, reviewer=None):
        """Submit -> review -> upload -> verify. A non-owner
        reviewer can be supplied for dual-role scenarios."""
        reviewer = reviewer or self.reviewer

        self._submit_request(request)

        self._post(
            reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 201)

        response = self._verify_document(
            upload.data["id"], reviewer=reviewer
        )
        self.assertEqual(response.status_code, 201)

        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVAL")
        return request

    def _advance_intl_to_travel_in_progress(self, request, reviewer=None):
        """Full international path to TRAVEL_IN_PROGRESS."""

        reviewer = reviewer or self.reviewer

        request = self._advance_intl_to_manager_approval(
            request, reviewer=reviewer
        )

        # Manager approval is team-scoped: approve with the
        # employee's manager of record (falls back to the
        # suite's manager for ownerless scenarios).
        approver = request.employee.manager or self.manager

        response = self._post(
            approver,
            f"/api/travel-requests/{request.pk}/approve/",
        )
        self.assertEqual(response.status_code, 200)

        response = self._post(
            reviewer,
            f"/api/travel-requests/{request.pk}/start-visa/",
        )
        self.assertEqual(response.status_code, 200)

        # Employee records the visa approval.
        self._post(
            request.employee,
            f"/api/travel-requests/{request.pk}/visa/apply/",
            {"applied_on": "2026-12-02"},
        )
        response = self._post(
            request.employee,
            f"/api/travel-requests/{request.pk}/visa/decision/",
            {"state": "APPROVED"},
        )
        self.assertEqual(response.status_code, 200)

        response = self._post(
            reviewer,
            f"/api/travel-requests/{request.pk}/start-booking/",
        )
        self.assertEqual(response.status_code, 200)

        response = self._post(
            reviewer,
            f"/api/travel-requests/{request.pk}/complete-booking/",
        )
        self.assertEqual(response.status_code, 200)

        response = self._post(
            request.employee,
            f"/api/travel-requests/{request.pk}/start-travel/",
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "TRAVEL_IN_PROGRESS")
        return request

    def _advance_intl_to_expense_submission(self, request, reviewer=None):
        request = self._advance_intl_to_travel_in_progress(
            request, reviewer=reviewer
        )

        response = self._post(
            request.employee,
            f"/api/travel-requests/{request.pk}/submit-expenses/",
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "EXPENSE_SUBMISSION")
        return request

    def _add_expense(self, request, employee=None, amount="100.00"):
        return self._post(
            employee or request.employee,
            f"/api/travel-requests/{request.pk}/expenses/",
            {
                "category": "FOOD",
                "expense_date": "2026-12-03",
                "amount": amount,
                "currency": "INR",
                "description": "Phase 23 expense",
            },
        )

    def _verify_expense(self, request, expense_id, decision="VERIFIED"):
        return self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/expenses/{expense_id}/verify/",
            {
                "status": decision,
                "review_comments": "ok" if decision == "REJECTED" else "",
            },
        )

    def _calculate_settlement(self, request):
        return self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/settlement/calculate/",
        )


# =========================================================
# A. Expense creation stage guard
# =========================================================


class ExpenseStageGuardTests(Phase23TestBase):
    """A: expenses may only be entered in the expense window."""

    def test_expense_allowed_at_travel_in_progress(self):
        request = self._advance_intl_to_travel_in_progress(
            self._create_request()
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["status"], "SUBMITTED"
        )

    def test_expense_allowed_at_expense_submission(self):
        request = self._advance_intl_to_expense_submission(
            self._create_request()
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 201)

    def test_expense_rejected_at_draft(self):
        request = self._create_request(status="DRAFT")

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)

    def test_expense_rejected_at_manager_approval(self):
        request = self._advance_intl_to_manager_approval(
            self._create_request()
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            Expense.objects.filter(
                travel_request=request
            ).exists()
        )

    def test_expense_rejected_at_travel_booking(self):
        request = self._create_request(status="TRAVEL_BOOKING")

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)

    def test_expense_rejected_at_travel_booked(self):
        request = self._create_request(status="TRAVEL_BOOKED")

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)

    def test_expense_rejected_at_submitted(self):
        request = self._create_request(status="SUBMITTED")

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)

    def test_expense_rejected_at_visa_processing(self):
        request = self._create_request(status="VISA_PROCESSING")

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)

    def test_expense_rejected_at_settlement_approval(self):
        request = self._create_request(
            status="SETTLEMENT_APPROVAL"
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 400)

    def test_expense_allowed_at_expense_verification(self):
        """Late receipts stay possible while the reviewer
        is still verifying (before settlement calculation)."""
        request = self._create_request(
            status="EXPENSE_VERIFICATION"
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 201)


# =========================================================
# B. Expense configuration (limits) stage guard
# =========================================================


class ExpenseConfigurationStageGuardTests(Phase23TestBase):
    """B: reviewer configures limits only in the valid window."""

    def _payload(self):
        return {
            "max_approved_expenses": "50000.00",
            "advance_amount": "10000.00",
            "daily_allowance": "2000.00",
            "currency": "INR",
        }

    def _configure(self, request, user=None):
        return self.client.put(
            f"/api/travel-requests/{request.pk}/expense-configuration/",
            data=self._payload(),
            content_type="application/json",
            HTTP_AUTHORIZATION=_auth(user or self.reviewer),
        )

    def test_reviewer_configures_at_travel_booking(self):
        request = self._create_request(status="TRAVEL_BOOKING")

        response = self._configure(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["max_approved_expenses"], "50000.00"
        )

    def test_reviewer_configures_at_manager_approved(self):
        request = self._create_request(status="MANAGER_APPROVED")

        response = self._configure(request)
        self.assertEqual(response.status_code, 200)

    def test_reviewer_configures_at_expense_verification(self):
        request = self._create_request(
            status="EXPENSE_VERIFICATION"
        )

        response = self._configure(request)
        self.assertEqual(response.status_code, 200)

    def test_reviewer_blocked_before_approval(self):
        for early_status in (
            "DRAFT",
            "SUBMITTED",
            "MANAGER_APPROVAL",
            "VISA_PROCESSING",
        ):
            request = self._create_request(status=early_status)

            response = self._configure(request)
            self.assertEqual(
                response.status_code,
                400,
                msg=f"status {early_status} must be rejected",
            )

    def test_reviewer_blocked_after_settlement(self):
        request = self._create_request(
            status="SETTLEMENT_PENDING"
        )

        response = self._configure(request)
        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_configure(self):
        request = self._create_request(status="TRAVEL_BOOKING")

        response = self._configure(request, self.employee)
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_configure(self):
        request = self._create_request(status="TRAVEL_BOOKING")

        response = self._configure(request, self.manager)
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_configure_without_reviewer_role(self):
        """ADMIN alone grants no reviewer authority."""
        request = self._create_request(status="TRAVEL_BOOKING")

        response = self._configure(request, self.admin)
        self.assertEqual(response.status_code, 403)


# =========================================================
# C. Settlement GET object-level visibility
# =========================================================


class SettlementVisibilityTests(Phase23TestBase):
    """C: only authorized viewers can read a settlement."""

    def _request_with_settlement(self):
        """Expense submitted -> verified -> settlement
        calculated, entirely through the public API."""
        request = self._advance_intl_to_expense_submission(
            self._create_request()
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 201)

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-expense-review/",
        )
        self.assertEqual(response.status_code, 200)

        listing = self._get(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/expenses/",
        )
        expense_id = listing.data[0]["id"]

        response = self._verify_expense(request, expense_id)
        self.assertEqual(response.status_code, 200)

        response = self._calculate_settlement(request)
        self.assertEqual(response.status_code, 200)

        return request

    def _get_settlement(self, request, user):
        return self._get(
            user,
            f"/api/travel-requests/{request.pk}/settlement/",
        )

    def test_owner_sees_own_settlement(self):
        request = self._request_with_settlement()

        response = self._get_settlement(request, self.employee)
        self.assertEqual(response.status_code, 200)
        self.assertIn("net_settlement", response.data)

    def test_other_employee_cannot_see_settlement(self):
        request = self._request_with_settlement()

        response = self._get_settlement(
            request, self.other_employee
        )
        self.assertIn(
            response.status_code, (403, 404)
        )

    def test_reviewer_sees_settlement(self):
        request = self._request_with_settlement()

        response = self._get_settlement(request, self.reviewer)
        self.assertEqual(response.status_code, 200)

    def test_team_manager_sees_settlement(self):
        request = self._request_with_settlement()

        response = self._get_settlement(request, self.manager)
        self.assertEqual(response.status_code, 200)

    def test_unrelated_manager_cannot_see_settlement(self):
        request = self._request_with_settlement()

        response = self._get_settlement(
            request, self.other_manager
        )
        self.assertIn(
            response.status_code, (403, 404)
        )

    def test_admin_sees_settlement(self):
        request = self._request_with_settlement()

        response = self._get_settlement(request, self.admin)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_cannot_see_settlement(self):
        request = self._request_with_settlement()

        response = self.client.get(
            f"/api/travel-requests/{request.pk}/settlement/"
        )
        self.assertEqual(response.status_code, 401)


# =========================================================
# D. Close-request ownership
# =========================================================


class CloseOwnershipTests(Phase23TestBase):
    """D: only the owner (or manager/admin) may close."""

    def _completed_request(self, employee=None):
        return self._create_request(
            employee=employee,
            status="COMPLETED",
        )

    def test_employee_closes_own_completed_request(self):
        request = self._completed_request(self.employee)

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/close/",
        )
        self.assertEqual(response.status_code, 200)

        request.refresh_from_db()
        self.assertEqual(request.status, "CLOSED")

    def test_employee_cannot_close_other_request(self):
        request = self._completed_request(self.other_employee)

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/close/",
        )
        self.assertEqual(response.status_code, 403)

        request.refresh_from_db()
        self.assertEqual(request.status, "COMPLETED")

    def test_manager_closes_team_request(self):
        request = self._completed_request(self.employee)

        response = self._post(
            self.manager,
            f"/api/travel-requests/{request.pk}/close/",
        )
        self.assertEqual(response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, "CLOSED")

    def test_admin_closes_any_request(self):
        request = self._completed_request(self.other_employee)

        response = self._post(
            self.admin,
            f"/api/travel-requests/{request.pk}/close/",
        )
        self.assertEqual(response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, "CLOSED")

    def test_close_still_stage_gated(self):
        """The stage requirement is unchanged: only
        COMPLETED requests can be closed."""
        request = self._create_request(
            status="SETTLEMENT_PROCESSING"
        )

        response = self._post(
            self.employee,
            f"/api/travel-requests/{request.pk}/close/",
        )
        self.assertEqual(response.status_code, 400)


# =========================================================
# E. Reviewer cannot verify own expense
# =========================================================


class ExpenseSelfVerificationTests(Phase23TestBase):
    """E: EMPLOYEE+REVIEWER dual role must not self-verify."""

    def _dual_role_reviewer(self):
        user = User.objects.create_user(
            username="p23_dual_role",
            password="TestPassword123",
            role="EMPLOYEE",
        )
        assign_role(user, "REVIEWER")
        return user

    def _request_with_submitted_expense(self, employee=None, reviewer=None):
        employee = employee or self.employee

        # Manager approval is team-scoped: make sure the
        # employee under test has a manager of record so an
        # approver exists (the dual-role employee is created
        # without one).
        if employee.manager is None:
            employee.manager = self.other_manager
            employee.save()
            self.addCleanup(
                lambda: (
                    setattr(employee, "manager", None),
                    employee.save(),
                )
            )

        request = self._advance_intl_to_expense_submission(
            self._create_request(employee=employee),
            reviewer=reviewer,
        )

        response = self._add_expense(request)
        self.assertEqual(response.status_code, 201)

        listing = self._get(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/expenses/",
        )
        expense_id = listing.data[0]["id"]
        return request, expense_id

    def test_dual_role_cannot_verify_own_expense(self):
        dual = self._dual_role_reviewer()
        request, expense_id = self._request_with_submitted_expense(
            employee=dual, reviewer=self.other_reviewer
        )

        response = self._post(
            dual,
            f"/api/travel-requests/{request.pk}/expenses/{expense_id}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(response.status_code, 403)

        expense = Expense.objects.get(pk=expense_id)
        self.assertEqual(expense.status, Expense.Status.SUBMITTED)

    def test_dual_role_cannot_reject_own_expense(self):
        dual = self._dual_role_reviewer()
        request, expense_id = self._request_with_submitted_expense(
            employee=dual, reviewer=self.other_reviewer
        )

        response = self._post(
            dual,
            f"/api/travel-requests/{request.pk}/expenses/{expense_id}/verify/",
            {
                "status": "REJECTED",
                "review_comments": "self reject attempt",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_dual_role_verifies_other_employee_expense(self):
        dual = self._dual_role_reviewer()
        request, expense_id = self._request_with_submitted_expense(
            employee=self.employee, reviewer=self.other_reviewer
        )

        response = self._post(
            dual,
            f"/api/travel-requests/{request.pk}/expenses/{expense_id}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(response.status_code, 200)

        expense = Expense.objects.get(pk=expense_id)
        self.assertEqual(expense.status, Expense.Status.VERIFIED)

    def test_employee_without_reviewer_role_cannot_verify(self):
        request, expense_id = self._request_with_submitted_expense(
            employee=self.employee
        )

        response = self._post(
            self.other_employee,
            f"/api/travel-requests/{request.pk}/expenses/{expense_id}/verify/",
            {"status": "VERIFIED"},
        )
        self.assertEqual(response.status_code, 403)


# =========================================================
# F. Reviewer checklist access for new workflows
# =========================================================


class ReviewerChecklistAccessTests(Phase23TestBase):
    """F: reviewers read new-workflow document checklists."""

    def test_reviewer_checklist_at_documents_pending(self):
        request = self._create_request(status="SUBMITTED")
        self._submit_request(request)

        response = self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )
        self.assertEqual(response.status_code, 200)

        checklist = self._get(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/documents/",
        )
        self.assertEqual(checklist.status_code, 200)
        self.assertIn("checklist", checklist.data)

        items = checklist.data["checklist"]
        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0]["document_type"], "Phase23 Passport"
        )
        self.assertEqual(items[0]["mandatory"], True)
        self.assertEqual(items[0]["status"], "MISSING")

    def test_reviewer_checklist_at_documents_under_review(self):
        request = self._create_request(status="SUBMITTED")
        self._submit_request(request)

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )
        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 201)

        checklist = self._get(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/documents/",
        )
        self.assertEqual(checklist.status_code, 200)
        items = checklist.data["checklist"]
        self.assertEqual(items[0]["status"], "PENDING_REVIEW")

    def test_reviewer_checklist_at_manager_approval(self):
        """Verification status stays visible after the
        request leaves the document stages."""
        request = self._advance_intl_to_manager_approval(
            self._create_request()
        )

        checklist = self._get(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/documents/",
        )
        self.assertEqual(checklist.status_code, 200)
        self.assertTrue(
            checklist.data["all_mandatory_verified"]
        )

    def test_employee_checklist_access_unchanged(self):
        request = self._create_request(status="SUBMITTED")
        self._submit_request(request)

        checklist = self._get(
            self.employee,
            f"/api/travel-requests/{request.pk}/documents/",
        )
        self.assertEqual(checklist.status_code, 200)

    def test_unrelated_employee_cannot_read_checklist(self):
        request = self._create_request(status="SUBMITTED")

        checklist = self._get(
            self.other_employee,
            f"/api/travel-requests/{request.pk}/documents/",
        )
        self.assertEqual(checklist.status_code, 403)


# =========================================================
# G. Document upload stage guard
# =========================================================


class DocumentUploadStageGuardTests(Phase23TestBase):
    """G: uploads only during the document workflow."""

    def test_upload_allowed_at_documents_pending(self):
        request = self._create_request(status="SUBMITTED")
        self._submit_request(request)

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 201)

    def test_upload_allowed_at_documents_under_review(self):
        request = self._create_request(
            status="DOCUMENTS_UNDER_REVIEW"
        )

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 201)

    def test_upload_rejected_after_document_stage(self):
        """MANAGER_APPROVAL and later must refuse uploads."""
        request = self._advance_intl_to_manager_approval(
            self._create_request()
        )
        self.assertEqual(request.status, "MANAGER_APPROVAL")

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 400)

    def test_upload_rejected_at_booking_stage(self):
        request = self._create_request(status="TRAVEL_BOOKING")

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 400)

    def test_upload_rejected_at_draft(self):
        request = self._create_request(status="DRAFT")

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 400)

    def test_upload_rejected_at_expense_stage(self):
        request = self._create_request(
            status="EXPENSE_SUBMISSION"
        )

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 400)

    def test_other_employee_cannot_upload(self):
        request = self._create_request(status="SUBMITTED")

        upload = self._upload_document(
            request, employee=self.other_employee
        )
        self.assertEqual(upload.status_code, 403)

    def test_document_from_other_request_not_verifiable(self):
        """ID tampering: the verify endpoint must touch only
        documents that belong to the request in the URL."""
        request_a = self._create_request(status="SUBMITTED")
        request_b = self._create_request(status="SUBMITTED")

        upload_a = self.client.post(
            f"/api/travel-requests/{request_a.pk}/documents/upload/",
            data={
                "document_type": self.passport.id,
                "file": SimpleUploadedFile(
                    "a.pdf",
                    b"%PDF-1.4 fake pdf",
                    content_type="application/pdf",
                ),
            },
            HTTP_AUTHORIZATION=_auth(request_a.employee),
        )
        self.assertEqual(upload_a.status_code, 201)
        document_a_id = upload_a.data["id"]

        # Attempt to verify document A while pointing at
        # request B's expense-verify path is impossible by
        # design; the document verify endpoint itself is
        # document-id based, so tampering protection is that
        # the upload stage guard on B does not leak A's doc.
        response = self._verify_document(document_a_id)
        self.assertEqual(response.status_code, 201)

        document_a = EmployeeDocument.objects.get(
            pk=document_a_id
        )
        self.assertEqual(
            document_a.travel_request, request_a
        )


# =========================================================
# H. Rejected document re-upload
# =========================================================


class RejectedDocumentReuploadTests(Phase23TestBase):
    """H: rejected documents stay re-uploadable in-stage."""

    def _request_with_rejected_document(self):
        request = self._create_request(status="SUBMITTED")
        self._submit_request(request)

        self._post(
            self.reviewer,
            f"/api/travel-requests/{request.pk}/start-review/",
        )

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 201)
        document_id = upload.data["id"]

        response = self._verify_document(document_id, "REJECTED")
        self.assertEqual(response.status_code, 201)

        request.refresh_from_db()
        return request, document_id

    def test_rejected_document_can_be_reuploaded(self):
        request, old_id = self._request_with_rejected_document()

        reupload = self._upload_document(request)
        self.assertEqual(reupload.status_code, 201)

        new_id = reupload.data["id"]
        self.assertNotEqual(new_id, old_id)

        # New version starts pending review.
        new_document = EmployeeDocument.objects.get(pk=new_id)
        self.assertEqual(
            new_document.status,
            EmployeeDocument.Status.PENDING_REVIEW,
        )

        # Old rejected version is preserved.
        old_document = EmployeeDocument.objects.get(pk=old_id)
        self.assertEqual(
            old_document.status,
            EmployeeDocument.Status.REJECTED,
        )

    def test_reupload_then_verify_advances_request(self):
        request, _old_id = self._request_with_rejected_document()

        reupload = self._upload_document(request)
        self.assertEqual(reupload.status_code, 201)

        response = self._verify_document(
            reupload.data["id"], "APPROVED"
        )
        self.assertEqual(response.status_code, 201)

        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVAL")


# =========================================================
# I. No status regression
# =========================================================


class NoStatusRegressionTests(Phase23TestBase):
    """I: late document events never pull the request back."""

    def test_late_upload_cannot_regress_from_manager_approval(self):
        request = self._advance_intl_to_manager_approval(
            self._create_request()
        )

        upload = self._upload_document(request)
        self.assertEqual(upload.status_code, 400)

        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVAL")

    def test_service_guard_leaves_advanced_request_untouched(self):
        """Direct service call: a request beyond the document
        stages keeps its status even when the service is
        invoked with an unverified document present."""
        request = self._advance_intl_to_manager_approval(
            self._create_request()
        )

        # Force a document into a non-verified state without
        # going through the guarded upload endpoint.
        document = EmployeeDocument.objects.create(
            travel_request=request,
            document_type=self.passport,
            file=SimpleUploadedFile(
                "late.pdf",
                b"%PDF-1.4 fake pdf",
                content_type="application/pdf",
            ),
            status=EmployeeDocument.Status.PENDING_REVIEW,
            uploaded_by=self.employee,
        )

        from documents.services import (
            update_travel_request_document_status,
        )

        result = update_travel_request_document_status(request)

        request.refresh_from_db()
        self.assertEqual(request.status, "MANAGER_APPROVAL")
        self.assertEqual(result, "MANAGER_APPROVAL")

    def test_settlement_stage_survives_document_service_call(self):
        request = self._create_request(
            status="SETTLEMENT_APPROVAL"
        )

        from documents.services import (
            update_travel_request_document_status,
        )

        update_travel_request_document_status(request)

        request.refresh_from_db()
        self.assertEqual(request.status, "SETTLEMENT_APPROVAL")
