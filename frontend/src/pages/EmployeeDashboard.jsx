import { useAuth } from "../hooks/useAuth";
import { Link } from "react-router-dom";

import NotificationList from "../components/NotificationList";
import { PageHeader, Card } from "../components/ui";

function EmployeeDashboard() {
  const { user } = useAuth();

  const displayName =
    user?.first_name || user?.username || "there";

  return (
    <>
      <PageHeader
        title={`Welcome, ${displayName}`}
        description={`${
          user?.employee_id ? `${user.employee_id} · ` : ""
        }${
          user?.department || "Employee workspace"
        } — plan, track, and settle your business travel.`}
      />

      <div className="page-section">
        <Card
          title="Travel management"
          subtitle="Start a new request or follow the ones already in progress."
        >
          <div className="btn-row">
            <Link to="/travel-requests/create" className="btn btn--primary">
              Create Travel Request
            </Link>

            <Link to="/travel-requests" className="btn btn--secondary">
              My Travel Requests
            </Link>
          </div>
        </Card>
      </div>

      <div className="page-section">
        <Card
          title="Notifications"
          subtitle="Updates about your requests, documents, and expenses."
        >
          <NotificationList compact />
        </Card>
      </div>
    </>
  );
}

export default EmployeeDashboard;
