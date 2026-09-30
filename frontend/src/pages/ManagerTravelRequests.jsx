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

function ManagerTravelRequests() {
  const navigate = useNavigate();

  const [travelRequests, setTravelRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTravelRequests = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await apiClient.get(
        "travel-requests/"
      );

      const data = response.data;

      if (Array.isArray(data)) {
        setTravelRequests(data);
      } else if (Array.isArray(data.results)) {
        setTravelRequests(data.results);
      } else {
        setTravelRequests([]);
      }
    } catch (err) {
      setError(extractApiError(err, "Failed to load travel requests."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void loadTravelRequests();
  }, []);

  if (loading) {
    return (
      <>
        <PageHeader
          title="Approval Queue"
          description="Travel requests submitted by your team."
        />
        <LoadingState label="Loading travel requests…" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Approval Queue"
        description="Travel requests submitted by your team."
        actions={
          <Button variant="secondary" onClick={loadTravelRequests} disabled={loading}>
            Refresh
          </Button>
        }
      />

      {error && travelRequests.length === 0 ? (
        <ErrorState
          title="Unable to load travel requests"
          message={error}
          onRetry={loadTravelRequests}
        />
      ) : travelRequests.length === 0 ? (
        <EmptyState
          icon="🏛"
          title="No travel requests found"
          description="Requests from your team will appear here once submitted for approval."
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
                {request.employee_name || "—"}
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
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    navigate(
                      `/manager/travel-requests/${request.id}`
                    )
                  }
                >
                  View Details
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

export default ManagerTravelRequests;
