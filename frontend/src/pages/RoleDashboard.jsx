import { useAuth } from "../hooks/useAuth";

import EmployeeDashboard from "./EmployeeDashboard";
import ReviewerDashboard from "./ReviewerDashboard";
import ManagerDashboard from "./ManagerDashboard";
import AdminDashboard from "./AdminDashboard";
import { hasAnyRole } from "../utils/roles";

function RoleDashboard() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: "30px" }}>
        <h2>Loading...</h2>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ padding: "30px" }}>
        <h2>User information not available</h2>
        <p>Please log in again.</p>
      </div>
    );
  }

  const views = [];

  // A user may hold several roles: render every relevant
  // dashboard. EMPLOYEE first (personal work), then the
  // business queues. ADMIN alone (no business role) sees
  // only the admin console.
  if (hasAnyRole(user, ["EMPLOYEE"])) {
    views.push(<EmployeeDashboard key="employee" />);
  }

  if (hasAnyRole(user, ["REVIEWER"])) {
    views.push(<ReviewerDashboard key="reviewer" />);
  }

  if (hasAnyRole(user, ["MANAGER"])) {
    views.push(<ManagerDashboard key="manager" />);
  }

  if (hasAnyRole(user, ["ADMIN"])) {
    views.push(<AdminDashboard key="admin" />);
  }

  if (views.length === 0) {
    return (
      <div style={{ padding: "30px" }}>
        <h1>Dashboard</h1>
        <p>
          Your roles (
          {(user.roles || [user.role]).join(", ") ||
            "none"}
          ) do not map to a dashboard.
        </p>
      </div>
    );
  }

  return <div>{views}</div>;
}

export default RoleDashboard;
