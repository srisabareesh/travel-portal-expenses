/**
 * Role helpers (Phase 16).
 *
 * The backend's `roles` array is the source of truth for
 * authorization visibility. The legacy single `role` field
 * is only a fallback for old sessions. Frontend role checks
 * are for UX only; the backend always enforces everything.
 */

export function getRoles(user) {
  if (!user) {
    return [];
  }

  if (Array.isArray(user.roles) && user.roles.length > 0) {
    return user.roles;
  }

  return user.role ? [user.role] : [];
}

export function hasRole(user, role) {
  return getRoles(user).includes(role);
}

export function hasAnyRole(user, roles) {
  return roles.some((role) => hasRole(user, role));
}

export const EMPLOYEE = "EMPLOYEE";
export const REVIEWER = "REVIEWER";
export const MANAGER = "MANAGER";
export const ADMIN = "ADMIN";
