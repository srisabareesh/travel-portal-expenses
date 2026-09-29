import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

import NotificationList from "../components/NotificationList";
import { PageHeader, Card, Button } from "../components/ui";

function ReviewerDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <>
      <PageHeader
        title={`Welcome, ${user?.first_name || user?.username || "Reviewer"}`}
        description="Verify employee travel documents and keep international requests moving."
      />

      <div className="page-section">
        <Card
          title="Document verification"
          subtitle="Requests waiting for document review appear in your queue."
          actions={
            <Button variant="primary" onClick={() => navigate("/reviewer/travel-requests")}>
              Open Review Queue
            </Button>
          }
        >
          <p className="secondary mb-0">
            You will verify uploaded documents, record visa decisions, and
            check expenses as requests progress.
          </p>
        </Card>
      </div>

      <div className="page-section">
        <Card
          title="Notifications"
          subtitle="Requests that need your attention."
        >
          <NotificationList compact />
        </Card>
      </div>

      <div className="page-section">
        <Card title="Quick links">
          <div className="btn-row">
            <Link to="/reviewer/travel-requests" className="btn btn--secondary">
              Review Queue
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

export default ReviewerDashboard;
