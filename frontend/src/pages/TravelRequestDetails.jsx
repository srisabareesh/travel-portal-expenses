import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../api/client";

import WorkflowProgress from "../components/WorkflowProgress";
import DocumentsCard from "../components/DocumentsCard";
import TravelSections from "../components/TravelSections";
import { useAuth } from "../hooks/useAuth";
import {
  PageHeader,
  Breadcrumb,
  Card,
  Button,
  TravelTypeBadge,
  RequestStatusBadge,
  LoadingState,
  ErrorState,
} from "../components/ui";
import { travelWindow } from "../lib/format";

function TravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [travelRequest, setTravelRequest] = useState(null);
  const [checklist, setChecklist] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchTravelRequestDetails = async () => {
    try {
      setLoading(true);
      setError("");

      const [requestResponse, checklistResponse] =
        await Promise.all([
          apiClient.get(`travel-requests/${id}/`),
          apiClient.get(`travel-requests/${id}/documents/`),
        ]);

      setTravelRequest(requestResponse.data);

      const checklistData = checklistResponse.data;

      if (Array.isArray(checklistData)) {
        setChecklist(checklistData);
      } else if (Array.isArray(checklistData.results)) {
        setChecklist(checklistData.results);
      } else if (Array.isArray(checklistData.checklist)) {
        setChecklist(checklistData.checklist);
      } else {
        setChecklist([]);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError("Travel request not found.");
      } else if (err.response?.status === 403) {
        setError(
          "You do not have permission to view this travel request."
        );
      } else if (err.response?.status === 401) {
        setError(
          "Your session has expired. Please login again."
        );
      } else {
        setError(
          "Failed to load travel request details."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void fetchTravelRequestDetails();
  }, [id]);

  if (loading) {
    return (
      <>
        <PageHeader
          title="Travel Request"
          description="Loading the request workspace…"
        />
        <LoadingState label="Loading travel request…" />
      </>
    );
  }

  if (error) {
    return (
      <>
        <Breadcrumb
          items={[
            { label: "Dashboard", to: "/dashboard" },
            { label: "Travel Requests", to: "/travel-requests" },
            { label: "Details" },
          ]}
        />
        <ErrorState
          title="Unable to open this travel request"
          message={error}
          onRetry={() => fetchTravelRequestDetails()}
        />
        <p className="mt-2">
          <Button variant="secondary" onClick={() => navigate("/travel-requests")}>
            Back to My Travel Requests
          </Button>
        </p>
      </>
    );
  }

  if (!travelRequest) {
    return null;
  }

  return (
    <>
      <Breadcrumb
        items={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Travel Requests", to: "/travel-requests" },
          { label: travelRequest.request_number || `#${id}` },
        ]}
      />

      <PageHeader
        title={`Request ${travelRequest.request_number || `#${id}`}`}
        description={`${travelRequest.destination_city || "—"}${
          travelRequest.country_name ? `, ${travelRequest.country_name}` : ""
        } · ${travelWindow(travelRequest.start_date, travelRequest.end_date)}`}
        actions={
          <>
            <RequestStatusBadge status={travelRequest.status} />
            <TravelTypeBadge type={travelRequest.travel_type} />
          </>
        }
      />

      {/* Request overview */}
      <Card title="Travel information" className="mb-3">
        <div className="meta-list">
          <div>
            <div className="meta-item-label">Employee</div>
            <div className="meta-item-value">
              {travelRequest.employee_name || "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Destination</div>
            <div className="meta-item-value">
              {travelRequest.destination_city || "—"}
              {travelRequest.country_name
                ? `, ${travelRequest.country_name}`
                : travelRequest.destination_country
                ? `, ${travelRequest.destination_country}`
                : ""}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Travel dates</div>
            <div className="meta-item-value">
              {travelWindow(travelRequest.start_date, travelRequest.end_date)}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Client</div>
            <div className="meta-item-value">
              {travelRequest.client || "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Project</div>
            <div className="meta-item-value">
              {travelRequest.project || "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Travel type</div>
            <div className="meta-item-value">
              <TravelTypeBadge type={travelRequest.travel_type} />
            </div>
          </div>
        </div>

        <div className="mt-2">
          <div className="meta-item-label">Purpose</div>
          <p className="meta-item-value mb-0" style={{ whiteSpace: "pre-wrap" }}>
            {travelRequest.purpose || "—"}
          </p>
        </div>
      </Card>

      {/* Workflow progress + guidance (backend-provided
          current status / next action / pending with), then
          documents and business sections in workflow order. */}
      <WorkflowProgress
        travelRequestId={id}
        onChanged={fetchTravelRequestDetails}
      />

      <DocumentsCard
        checklist={checklist}
        uploadBaseUrl={`/travel-requests/${id}/documents/upload`}
        canUpload={
          travelRequest.status === "SUBMITTED" ||
          travelRequest.status === "DOCUMENTS_PENDING" ||
          travelRequest.status === "DOCUMENTS_UNDER_REVIEW"
        }
      />

      <TravelSections
        travelRequestId={id}
        travelRequest={travelRequest}
        user={user}
      />

      <p className="mt-3">
        <Button variant="ghost" size="sm" onClick={fetchTravelRequestDetails}>
          ↻ Refresh
        </Button>
      </p>
    </>
  );
}

export default TravelRequestDetails;
