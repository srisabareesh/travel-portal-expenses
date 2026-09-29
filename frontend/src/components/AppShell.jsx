import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { hasAnyRole } from "../utils/roles";
import { roleLabel } from "../lib/format";

/**
 * AppShell — the application frame: responsive sidebar (role-aware),
 * mobile top bar, and the routed page content.
 *
 * Navigation visibility follows the backend-provided roles[] array.
 * The backend enforces every permission; the sidebar is UX only.
 */

const BRAND = "Travel Portal";

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  const isEmployee = hasAnyRole(user, ["EMPLOYEE"]);
  const isReviewer = hasAnyRole(user, ["REVIEWER"]);
  const isManager = hasAnyRole(user, ["MANAGER"]);
  const isAdmin = hasAnyRole(user, ["ADMIN"]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const linkClass = ({ isActive }) =>
    `app-sidebar-link${isActive ? " active" : ""}`;

  const renderLink = (to, icon, label) => (
    <NavLink to={to} className={linkClass} onClick={closeMenu}>
      <span className="app-sidebar-link-icon" aria-hidden="true">
        {icon}
      </span>
      {label}
    </NavLink>
  );

  return (
    <div className="app-shell">
      {menuOpen && (
        <button
          type="button"
          className="sidebar-scrim open"
          aria-label="Close navigation"
          onClick={closeMenu}
        />
      )}

      <aside className={`app-sidebar${menuOpen ? " open" : ""}`} aria-label="Main navigation">
        <div className="app-sidebar-brand">
          <span className="app-sidebar-brand-mark" aria-hidden="true">
            ✈
          </span>
          {BRAND}
        </div>

        <nav className="app-sidebar-nav">
          <div className="app-sidebar-group">
            <p className="app-sidebar-group-label">Overview</p>
            {renderLink("/dashboard", "▤", "Dashboard")}
            {isEmployee && renderLink("/notifications", "🔔", "Notifications")}
          </div>

          {isEmployee && (
            <div className="app-sidebar-group">
              <p className="app-sidebar-group-label">Travel</p>
              {renderLink("/travel-requests", "🧾", "My Travel Requests")}
              {renderLink("/travel-requests/create", "＋", "Create Travel Request")}
            </div>
          )}

          {isReviewer && (
            <div className="app-sidebar-group">
              <p className="app-sidebar-group-label">Review</p>
              {renderLink("/reviewer/travel-requests", "✓", "Review Queue")}
            </div>
          )}

          {isManager && (
            <div className="app-sidebar-group">
              <p className="app-sidebar-group-label">Approvals</p>
              {renderLink("/manager/travel-requests", "🏛", "Approval Queue")}
            </div>
          )}

          {isAdmin && (
            <div className="app-sidebar-group">
              <p className="app-sidebar-group-label">Administration</p>
              {renderLink("/admin", "⚙", "Administration")}
            </div>
          )}
        </nav>

        <div className="app-sidebar-footer">
          <div className="app-sidebar-user">
            <div className="app-sidebar-user-name">
              {user?.first_name || user?.username || "Signed in"}
            </div>
            <div className="app-sidebar-user-meta">
              {user?.employee_id ? `${user.employee_id} · ` : ""}
              {(user?.roles || [])
                .map((role) => roleLabel(role))
                .join(", ") || roleLabel(user?.role)}
            </div>
          </div>
          <button type="button" className="app-sidebar-link" onClick={handleLogout}>
            <span className="app-sidebar-link-icon" aria-hidden="true">
              ⎋
            </span>
            Logout
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            ☰ Menu
          </button>

          <div className="app-topbar-brand">
            <span className="app-sidebar-brand-mark" aria-hidden="true">
              ✈
            </span>
            {BRAND}
          </div>

          <button type="button" className="btn btn--secondary btn--sm" onClick={handleLogout}>
            Logout
          </button>
        </header>

        <main className="app-content" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
