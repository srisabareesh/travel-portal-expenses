"""
Phase 2 foundation tests.

Covers:
    * Role model and the four seeded standard roles
    * Explicit multi-role assignment (with duplicate prevention)
    * has_role() / legacy role synchronization
    * ADMIN does NOT implicitly receive business authority
    * Automatic EMP-###### employee ID generation
    * Authentication regression (login, refresh, /api/auth/me)
    * Manager approval authorization still enforced
"""

from django.test import TestCase

from rest_framework.test import APIRequestFactory

from users.models import User, Role
from users.permissions import (
    IsAdmin,
    IsEmployee,
    IsManager,
    IsReviewer,
    IsReviewerOrManager,
)
from users.services import (
    assign_role,
    ensure_roles_seeded,
    generate_employee_id,
    sync_legacy_role,
)

from travel.models import Country, TravelRequest


def make_permission_request(user):
    """Build a minimal DRF request for permission-class checks."""
    factory = APIRequestFactory()
    request = factory.get("/api/")
    request.user = user
    return request


class RoleModelTests(TestCase):
    """
    Tests 1-2: role creation and the four standard roles.

    The four standard roles are seeded automatically by the
    users.0003_seed_roles migration when the database (or the
    test database) is created, so they must already exist here.
    """

    def test_standard_roles_exist_after_migrations(self):
        names = set(
            Role.objects.values_list("name", flat=True)
        )

        self.assertEqual(
            names,
            {"EMPLOYEE", "REVIEWER", "MANAGER", "ADMIN"},
        )

    def test_role_model_allows_creation(self):
        role = Role.objects.create(
            name="TESTROLE",
            description="Temporary role",
        )

        self.assertEqual(role.name, "TESTROLE")
        self.assertTrue(role.is_active)

    def test_role_name_is_unique(self):
        ##ADMIN already exists from the seed migration:
        ##creating it again must violate the unique constraint.
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Role.objects.create(name=Role.Name.ADMIN)


class RoleAssignmentTests(TestCase):
    """Tests 3-6: assignment, multi-role, duplicates, has_role()."""

    def setUp(self):
        ensure_roles_seeded()
        self.user = User.objects.create_user(
            username="employee1",
            password="TestPassword123",
        )

    def test_assign_single_role(self):
        ##New users are bootstrapped with EMPLOYEE by the
        ##post_save signal; assigning an additional role adds it.
        added = assign_role(self.user, Role.Name.MANAGER)

        self.assertTrue(added)
        self.assertTrue(
            self.user.has_role(Role.Name.MANAGER)
        )

    def test_assigning_already_held_role_is_idempotent(self):
        ##EMPLOYEE was already assigned at creation time.
        added_again = assign_role(self.user, Role.Name.EMPLOYEE)

        self.assertFalse(added_again)

        self.assertEqual(
            self.user.roles.filter(
                name=Role.Name.EMPLOYEE
            ).count(),
            1,
        )

    def test_assign_multiple_roles(self):
        assign_role(self.user, Role.Name.ADMIN)
        assign_role(self.user, Role.Name.REVIEWER)

        ##Plus the EMPLOYEE role assigned automatically at creation.
        self.assertEqual(
            set(self.user.get_role_names()),
            {"EMPLOYEE", "ADMIN", "REVIEWER"},
        )

    def test_duplicate_role_assignment_is_prevented(self):
        assign_role(self.user, Role.Name.MANAGER)
        added_again = assign_role(self.user, Role.Name.MANAGER)

        self.assertFalse(added_again)

        self.assertEqual(
            self.user.roles.filter(
                name=Role.Name.MANAGER
            ).count(),
            1,
        )

    def test_has_role_is_explicit_membership_only(self):
        assign_role(self.user, Role.Name.EMPLOYEE)

        self.assertTrue(self.user.has_role("EMPLOYEE"))
        self.assertFalse(self.user.has_role("ADMIN"))
        self.assertFalse(self.user.has_role("MANAGER"))
        self.assertFalse(self.user.has_role("REVIEWER"))

    def test_legacy_role_field_stays_in_sync(self):
        assign_role(self.user, Role.Name.REVIEWER)
        assign_role(self.user, Role.Name.ADMIN)

        self.user.refresh_from_db()

        ##Highest-priority role wins the legacy single field.
        self.assertEqual(self.user.role, "ADMIN")


class AdminPermissionSeparationTests(TestCase):
    """Tests 7-10: ADMIN grants no implicit business authority."""

    def setUp(self):
        ensure_roles_seeded()

    def make_user_with_roles(self, username, *role_names):
        user = User.objects.create_user(
            username=username,
            password="TestPassword123",
        )

        for role_name in role_names:
            assign_role(user, role_name)

        return user

    def test_admin_only_user_has_no_manager_permission(self):
        admin = self.make_user_with_roles("admin1", Role.Name.ADMIN)

        self.assertTrue(IsAdmin().has_permission(make_permission_request(admin), None))
        self.assertFalse(IsManager().has_permission(make_permission_request(admin), None))

    def test_admin_only_user_has_no_reviewer_permission(self):
        admin = self.make_user_with_roles("admin2", Role.Name.ADMIN)

        self.assertFalse(IsReviewer().has_permission(make_permission_request(admin), None))
        self.assertFalse(IsReviewerOrManager().has_permission(make_permission_request(admin), None))

    def test_admin_plus_manager_has_manager_permission(self):
        admin_manager = self.make_user_with_roles(
            "admin_manager",
            Role.Name.ADMIN,
            Role.Name.MANAGER,
        )

        self.assertTrue(
            IsManager().has_permission(
                make_permission_request(admin_manager), None
            )
        )
        self.assertTrue(
            IsAdmin().has_permission(
                make_permission_request(admin_manager), None
            )
        )

    def test_admin_plus_reviewer_has_reviewer_permission(self):
        admin_reviewer = self.make_user_with_roles(
            "admin_reviewer",
            Role.Name.ADMIN,
            Role.Name.REVIEWER,
        )

        self.assertTrue(
            IsReviewer().has_permission(
                make_permission_request(admin_reviewer), None
            )
        )

    def test_admin_only_user_cannot_approve_travel_requests(self):
        """
        End-to-end: an ADMIN-only user hitting the manager
        approval endpoint must be rejected.
        """
        admin = self.make_user_with_roles("admin3", Role.Name.ADMIN)

        employee = self.make_user_with_roles("emp9", Role.Name.EMPLOYEE)
        country = Country.objects.create(
            name="Germany",
            country_code="DE",
        )
        request = TravelRequest.objects.create(
            employee=employee,
            destination_country=country,
            destination_city="Berlin",
            travel_type=TravelRequest.TravelType.BUSINESS,
            start_date="2026-10-01",
            end_date="2026-10-05",
            purpose="Client workshop",
        )

        self.client.force_login = None
        from rest_framework_simplejwt.authentication import JWTAuthentication  # noqa: F401

        response = self.client.post(
            f"/api/travel-requests/{request.pk}/approve/",
            HTTP_AUTHORIZATION=self._jwt(admin),
        )

        self.assertEqual(
            response.status_code,
            403,
            msg="ADMIN-only user must not have approval authority",
        )

    def _jwt(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        return f"Bearer {RefreshToken.for_user(user).access_token}"


class LegacyRoleBootstrapTests(TestCase):
    """Existing user-creation paths keep working unchanged."""

    def setUp(self):
        ensure_roles_seeded()

    def test_creating_user_with_legacy_role_bootstraps_roles(self):
        user = User.objects.create_user(
            username="manager1",
            password="TestPassword123",
            role="MANAGER",
        )

        self.assertTrue(user.has_role(Role.Name.MANAGER))

    def test_default_user_becomes_employee(self):
        user = User.objects.create_user(
            username="default1",
            password="TestPassword123",
        )

        self.assertTrue(user.has_role(Role.Name.EMPLOYEE))
        self.assertEqual(user.role, "EMPLOYEE")

    def test_removing_role_updates_legacy_field(self):
        user = User.objects.create_user(
            username="mixed1",
            password="TestPassword123",
            role="REVIEWER",
        )

        assign_role(user, Role.Name.ADMIN)
        user.roles.remove(Role.objects.get(name=Role.Name.ADMIN))

        user.refresh_from_db()

        self.assertEqual(user.role, "REVIEWER")

    def test_manual_sync_helper_matches_roles(self):
        user = User.objects.create_user(
            username="sync1",
            password="TestPassword123",
        )

        assign_role(user, Role.Name.MANAGER)

        ##Force a stale legacy value and re-sync.
        User.objects.filter(pk=user.pk).update(role="EMPLOYEE")
        user.refresh_from_db()
        self.assertEqual(user.role, "EMPLOYEE")

        sync_legacy_role(user)
        self.assertEqual(user.role, "MANAGER")


class EmployeeIdGenerationTests(TestCase):
    """Tests 11-16: automatic EMP-###### generation."""

    def setUp(self):
        ensure_roles_seeded()

    def test_first_user_gets_emp_000001(self):
        user = User.objects.create_user(
            username="first",
            password="TestPassword123",
        )

        self.assertEqual(user.employee_id, "EMP-000001")

    def test_employee_id_format(self):
        import re

        user = User.objects.create_user(
            username="format",
            password="TestPassword123",
        )

        self.assertRegex(user.employee_id, r"^EMP-\d{6}$")

    def test_employee_ids_are_unique(self):
        created_ids = set()

        for index in range(25):
            user = User.objects.create_user(
                username=f"bulk{index}",
                password="TestPassword123",
            )

            self.assertNotIn(user.employee_id, created_ids)
            created_ids.add(user.employee_id)

        self.assertEqual(len(created_ids), 25)

    def test_employee_ids_are_sequential(self):
        first = User.objects.create_user(
            username="seq1",
            password="TestPassword123",
        )
        second = User.objects.create_user(
            username="seq2",
            password="TestPassword123",
        )
        third = User.objects.create_user(
            username="seq3",
            password="TestPassword123",
        )

        self.assertEqual(first.employee_id, "EMP-000001")
        self.assertEqual(second.employee_id, "EMP-000002")
        self.assertEqual(third.employee_id, "EMP-000003")

    def test_deactivated_user_id_is_not_reused(self):
        active = User.objects.create_user(
            username="active1",
            password="TestPassword123",
        )
        deactivated = User.objects.create_user(
            username="gone1",
            password="TestPassword123",
        )

        deactivated.is_active = False
        deactivated.save()

        self.assertEqual(deactivated.employee_id, "EMP-000002")

        next_user = User.objects.create_user(
            username="next1",
            password="TestPassword123",
        )

        ##EMP-000002 belongs to the deactivated user forever.
        self.assertNotEqual(next_user.employee_id, "EMP-000002")
        self.assertEqual(next_user.employee_id, "EMP-000003")

        ##The deactivated user keeps their ID.
        deactivated.refresh_from_db()
        self.assertEqual(deactivated.employee_id, "EMP-000002")
        self.assertEqual(active.employee_id, "EMP-000001")

    def test_manual_employee_ids_remain_unchanged(self):
        manual = User.objects.create_user(
            username="manual1",
            password="TestPassword123",
            employee_id="LEGACY-007",
        )

        self.assertEqual(manual.employee_id, "LEGACY-007")

        ##Editing other fields must never touch the ID.
        manual.department = "Engineering"
        manual.save()
        manual.refresh_from_db()

        self.assertEqual(manual.employee_id, "LEGACY-007")

        ##Generation skips past manual IDs and continues
        ##from the highest system-generated number.
        generated = User.objects.create_user(
            username="after_manual",
            password="TestPassword123",
        )

        self.assertEqual(generated.employee_id, "EMP-000001")

    def test_generation_handles_large_manual_system_ids(self):
        User.objects.create_user(
            username="big",
            password="TestPassword123",
            employee_id="EMP-999999",
        )

        self.assertEqual(generate_employee_id(), "EMP-1000000")

    def test_explicit_blank_string_generates_id(self):
        user = User(
            username="blankid",
            employee_id="   ",
        )
        user.set_password("TestPassword123")
        user.save()
        user.refresh_from_db()

        self.assertRegex(user.employee_id, r"^EMP-\d{6}$")


class AuthenticationRegressionTests(TestCase):
    """Tests 17-18: JWT login, refresh and /api/auth/me."""

    def setUp(self):
        ensure_roles_seeded()
        self.user = User.objects.create_user(
            username="authuser",
            password="TestPassword123",
            first_name="Auth",
            last_name="User",
            department="Engineering",
        )

    def _login_tokens(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "authuser",
                "password": "TestPassword123",
            },
        )

        self.assertEqual(response.status_code, 200)

        return response.data

    def test_jwt_login_still_works(self):
        data = self._login_tokens()

        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_refresh_token_still_works(self):
        data = self._login_tokens()

        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": data["refresh"]},
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=response.content,
        )
        self.assertIn("access", response.data)

    def test_auth_me_still_works(self):
        data = self._login_tokens()

        response = self.client.get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {data['access']}",
        )

        self.assertEqual(response.status_code, 200)

        payload = response.data

        self.assertEqual(payload["username"], "authuser")
        self.assertEqual(payload["employee_id"], "EMP-000001")
        self.assertEqual(payload["role"], "EMPLOYEE")
        self.assertEqual(payload["roles"], ["EMPLOYEE"])

    def test_auth_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_protected_view_rejects_missing_token(self):
        response = self.client.get("/api/travel-requests/")

        self.assertEqual(
            response.status_code,
            401,
        )


class ManagerApprovalAuthorizationTests(TestCase):
    """
    Regression: team scoping, self-approval ban and the new
    explicit-manager requirement all keep working through the
    existing approve endpoint.
    """

    def setUp(self):
        ensure_roles_seeded()

        self.country = Country.objects.create(
            name="Germany",
            country_code="DE",
        )

        self.employee = User.objects.create_user(
            username="emp_approve",
            password="TestPassword123",
            role="EMPLOYEE",
        )
        self.team_manager = User.objects.create_user(
            username="mgr_approve",
            password="TestPassword123",
            role="MANAGER",
        )
        self.other_manager = User.objects.create_user(
            username="mgr_other",
            password="TestPassword123",
            role="MANAGER",
        )

        self.employee.manager = self.team_manager
        self.employee.save()

        self.travel_request = TravelRequest.objects.create(
            employee=self.employee,
            destination_country=self.country,
            destination_city="Berlin",
            travel_type=TravelRequest.TravelType.BUSINESS,
            start_date="2026-10-01",
            end_date="2026-10-05",
            purpose="Client workshop",
        )

    def _auth(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        return f"Bearer {RefreshToken.for_user(user).access_token}"

    def _post_approve(self, user):
        return self.client.post(
            f"/api/travel-requests/{self.travel_request.pk}/approve/",
            HTTP_AUTHORIZATION=self._auth(user),
        )

    def test_manager_cannot_approve_own_request(self):
        own_request = TravelRequest.objects.create(
            employee=self.team_manager,
            destination_country=self.country,
            destination_city="Munich",
            travel_type=TravelRequest.TravelType.BUSINESS,
            start_date="2026-10-01",
            end_date="2026-10-05",
            purpose="Own travel",
        )

        response = self.client.post(
            f"/api/travel-requests/{own_request.pk}/approve/",
            HTTP_AUTHORIZATION=self._auth(self.team_manager),
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_approve_unrelated_employee(self):
        response = self._post_approve(self.other_manager)

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_approve(self):
        response = self._post_approve(self.employee)

        self.assertEqual(response.status_code, 403)

    def test_team_manager_passes_authorization_gate(self):
        """
        The team manager gets past every permission check;
        the request fails only on workflow status (400),
        proving authorization still works end-to-end.
        """
        response = self._post_approve(self.team_manager)

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)


class LegacyTravelTypeRoleRegressionTests(TestCase):
    """
    Phase 3.2: Phase 2 role/permission behavior must keep
    working for records that carry a historical travel type.
    """

    def setUp(self):
        ensure_roles_seeded()

        self.country = Country.objects.create(
            name="Regression Land",
            country_code="RL",
        )

        self.employee = User.objects.create_user(
            username="emp_legacy",
            password="TestPassword123",
            role="EMPLOYEE",
        )
        self.team_manager = User.objects.create_user(
            username="mgr_legacy",
            password="TestPassword123",
            role="MANAGER",
        )
        self.other_manager = User.objects.create_user(
            username="mgr_legacy_other",
            password="TestPassword123",
            role="MANAGER",
        )

        self.employee.manager = self.team_manager
        self.employee.save()

        self.legacy_request = TravelRequest.objects.create(
            employee=self.employee,
            destination_country=self.country,
            destination_city="Legacy Town",
            travel_type=TravelRequest.TravelType.BUSINESS,
            start_date="2026-10-01",
            end_date="2026-10-05",
            purpose="Historical role regression",
        )

    def _auth(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        return f"Bearer {RefreshToken.for_user(user).access_token}"

    def test_manager_can_view_team_legacy_request(self):

        response = self.client.get(
            f"/api/travel-requests/{self.legacy_request.pk}/",
            HTTP_AUTHORIZATION=self._auth(self.team_manager),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["travel_type"],
            "BUSINESS",
        )

        self.assertTrue(
            response.data["travel_type_is_legacy"]
        )

    def test_other_manager_cannot_view_legacy_request(self):

        response = self.client.get(
            f"/api/travel-requests/{self.legacy_request.pk}/",
            HTTP_AUTHORIZATION=self._auth(self.other_manager),
        )

        self.assertEqual(response.status_code, 404)

    def test_approve_authorization_unchanged_for_legacy_request(self):

        response = self.client.post(
            f"/api/travel-requests/{self.legacy_request.pk}/approve/",
            HTTP_AUTHORIZATION=self._auth(self.team_manager),
        )

        ##The team manager passes authorization and is
        ##rejected only on workflow status (request is
        ##DRAFT, not DOCUMENT_VERIFICATION).
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)

        self.other_manager_response = self.client.post(
            f"/api/travel-requests/{self.legacy_request.pk}/approve/",
            HTTP_AUTHORIZATION=self._auth(self.other_manager),
        )

        self.assertEqual(
            self.other_manager_response.status_code,
            403,
        )
