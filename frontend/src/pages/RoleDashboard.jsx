import { useAuth } from "../hooks/useAuth";

import EmployeeDashboard from "./EmployeeDashboard";
import ReviewerDashboard from "./ReviewerDashboard";
import ManagerDashboard from "./ManagerDashboard";
import AdminDashboard from "./AdminDashboard";
import { hasAnyRole } from "../utils/roles";
import { LoadingState, EmptyState, PageHeader } from "../components/ui";

function RoleDashboard() {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingState label="Loading your dashboard…" />;
  }

  if (!user) {
    return (
      <EmptyState
        icon="👤"
        title="User information not available"
        description="Please log in again to continue."
      />
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
    views.push(<AdminDashboard key="admin" showAsDashboard />);
  }

  if (views.length === 0) {
    return (
      <>
        <PageHeader
          title="Dashboard"
          description="Your account is not linked to any dashboard yet."
        />
        <EmptyState
          icon="🗂️"
          title="No dashboard available"
          description="Your roles do not map to a dashboard. Please contact your administrator."
        />
      </>
    );
  }

  return <div className="stack">{views}</div>;
}

export default RoleDashboard;
