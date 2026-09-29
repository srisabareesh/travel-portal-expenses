import { Link, useNavigate } from "react-router-dom";

import NotificationList from "../components/NotificationList";
import { PageHeader, Card, Button } from "../components/ui";

function ManagerDashboard() {
  const navigate = useNavigate();

  return (
    <>
      <PageHeader
        title="Manager Dashboard"
        description="Review your team's travel requests and make the final decision."
      />

      <div className="page-section">
        <Card
          title="Pending approvals"
          subtitle="Requests awaiting manager approval appear in your queue."
          actions={
            <Button variant="primary" onClick={() => navigate("/manager/travel-requests")}>
              Open Approval Queue
            </Button>
          }
        >
          <p className="secondary mb-0">
            Check document readiness and travel details before approving or
            rejecting each request.
          </p>
        </Card>
      </div>

      <div className="page-section">
        <Card
          title="Notifications"
          subtitle="Team requests and settlement updates."
        >
          <NotificationList compact />
        </Card>
      </div>

      <div className="page-section">
        <Card title="Quick links">
          <div className="btn-row">
            <Link to="/manager/travel-requests" className="btn btn--secondary">
              Approval Queue
            </Link>
            <Link to="/notifications" className="btn btn--secondary">
              All Notifications
            </Link>
          </div>
        </Card>
      </div>
    </>
  );
}

export default ManagerDashboard;
