import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

import {
  PageHeader,
  Button,
  Table,
  RequestStatusBadge,
  TravelTypeBadge,
  LoadingState,
  EmptyState,
  ErrorState,
} from "../components/ui";
import {
  extractApiError,
  travelWindow,
} from "../lib/format";

function ReviewerTravelRequests() {
  const navigate = useNavigate();

  const [travelRequests, setTravelRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchTravelRequests = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await apiClient.get(
        "travel-requests/"
      );

      setTravelRequests(response.data);
    } catch (err) {
      if (err.response?.status === 401) {
        setError("Your session has expired. Please login again.");
      } else if (err.response?.status === 403) {
        setError(
          "You do not have permission to view these travel requests."
        );
      } else {
        setError(extractApiError(err, "Failed to load travel requests."));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void fetchTravelRequests();
  }, []);

  if (loading) {
    return (
      <>
        <PageHeader
          title="Review Queue"
          description="Travel requests awaiting document verification."
        />
        <LoadingState label="Loading travel requests…" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Review Queue"
        description="Travel requests awaiting document verification."
        actions={
          <Button variant="secondary" onClick={fetchTravelRequests} disabled={loading}>
            Refresh
          </Button>
        }
      />

      {error && travelRequests.length === 0 ? (
        <ErrorState
          title="Unable to load travel requests"
          message={error}
          onRetry={fetchTravelRequests}
        />
      ) : travelRequests.length === 0 ? (
        <EmptyState
          icon="✓"
          title="No travel requests to review"
          description="You are all caught up. New requests will appear here when employees submit documents."
        />
      ) : (
        <Table
          columns={[
            { key: "request", label: "Request" },
            { key: "employee", label: "Employee" },
            { key: "destination", label: "Destination" },
            { key: "type", label: "Travel Type" },
            { key: "dates", label: "Travel Dates" },
            { key: "status", label: "Status" },
            { key: "action", label: "Action", align: "right" },
          ]}
        >
          {travelRequests.map((request) => (
            <tr key={request.id}>
              <td>
                <div className="cell-strong mono">{request.request_number}</div>
                <div className="cell-secondary">{request.client || "—"}</div>
              </td>

              <td>
                {request.employee_name || `Employee ID: ${request.employee}`}
              </td>

              <td>
                <div className="cell-strong">
                  {request.destination_city || "—"}
                </div>
                <div className="cell-secondary">
                  {request.country_name || request.destination_country || ""}
                </div>
              </td>

              <td>
                <TravelTypeBadge type={request.travel_type} />
              </td>

              <td>{travelWindow(request.start_date, request.end_date)}</td>

              <td>
                <RequestStatusBadge status={request.status} />
              </td>

              <td style={{ textAlign: "right" }}>
                <Button
                  size="sm"
                  onClick={() =>
                    navigate(
                      `/reviewer/travel-requests/${request.id}`
                    )
                  }
                >
                  Review
                </Button>
              </td>
            </tr>
          ))}
        </Table>
      )}

      <p className="mt-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
          ← Back to Dashboard
        </Button>
      </p>
    </>
  );
}

export default ReviewerTravelRequests;
