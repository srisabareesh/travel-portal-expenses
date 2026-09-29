import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import apiClient from "../api/client";

import WorkflowProgress from "../components/WorkflowProgress";
import TravelSections from "../components/TravelSections";
import {
  PageHeader,
  Breadcrumb,
  Card,
  Button,
  Table,
  DocumentStatusBadge,
  TravelTypeBadge,
  RequestStatusBadge,
  LoadingState,
  ErrorState,
} from "../components/ui";
import { formatDate, travelWindow } from "../lib/format";

function TravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

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

  const totalDocuments = checklist.length;

  const verifiedDocuments = checklist.filter(
    (document) => document.status === "VERIFIED"
  ).length;

  const missingDocuments = checklist.filter(
    (document) =>
      document.status === "MISSING" ||
      document.status === "REJECTED"
  ).length;

  const pendingDocuments = checklist.filter(
    (document) =>
      document.status === "UPLOADED" ||
      document.status === "PENDING_REVIEW" ||
      document.status === "EXPIRING_SOON"
  ).length;

  const completionPercentage =
    totalDocuments > 0
      ? Math.round((verifiedDocuments / totalDocuments) * 100)
      : 0;

  const needsDocumentAction = checklist.some(
    (document) =>
      document.status === "MISSING" ||
      document.status === "REJECTED"
  );

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
              {travelRequest.employee_name || travelRequest.employee || "—"}
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

      {/* Workflow progress + business sections (Phase 16/17) */}
      <WorkflowProgress
        travelRequestId={id}
        onChanged={fetchTravelRequestDetails}
      />

      <TravelSections travelRequestId={id} />

      {/* Documents */}
      {totalDocuments > 0 && (
        <Card
          title="Documents"
          subtitle={
            needsDocumentAction
              ? "Some documents are missing or were rejected — upload them to continue."
              : `${verifiedDocuments} of ${totalDocuments} documents verified.`
          }
          className="mb-3"
          actions={
            needsDocumentAction ? (
              <Link
                to={`/travel-requests/${id}/documents/upload`}
                className="btn btn--primary"
              >
                Upload Required Document
              </Link>
            ) : undefined
          }
        >
          <div className="flex-between mb-1">
            <span className="secondary">
              <strong>{verifiedDocuments}</strong> of{" "}
              <strong>{totalDocuments}</strong> verified
            </span>
            <span className="secondary">{completionPercentage}%</span>
          </div>

          <div className="progress" role="progressbar" aria-valuenow={completionPercentage} aria-valuemin={0} aria-valuemax={100} aria-label="Document verification progress">
            <div
              className="progress-bar"
              style={{ width: `${completionPercentage}%` }}
            />
          </div>

          <div className="kpi-grid mt-2" style={{ marginBottom: 0 }}>
            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Total</div>
              <div className="kpi-value">{totalDocuments}</div>
            </div>

            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Verified</div>
              <div className="kpi-value kpi-value--success">
                {verifiedDocuments}
              </div>
            </div>

            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Pending</div>
              <div className="kpi-value kpi-value--warning">
                {pendingDocuments}
              </div>
            </div>

            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Missing / Rejected</div>
              <div className="kpi-value kpi-value--danger">
                {missingDocuments}
              </div>
            </div>
          </div>

          <div className="mt-3">
            <Table
              compact
              columns={[
                { key: "document", label: "Document" },
                { key: "mandatory", label: "Required" },
                { key: "status", label: "Status" },
                { key: "expiry", label: "Expiry" },
                { key: "action", label: "Action", align: "right" },
              ]}
            >
              {checklist.map((document) => (
                <tr key={document.document_type_id}>
                  <td className="cell-strong">
                    {document.document_type || "—"}
                  </td>

                  <td>{document.mandatory ? "Yes" : "No"}</td>

                  <td>
                    <DocumentStatusBadge status={document.status} />
                  </td>

                  <td>{formatDate(document.expiry_date)}</td>

                  <td style={{ textAlign: "right" }}>
                    {document.status === "MISSING" ||
                    document.status === "REJECTED" ? (
                      <Link
                        to={`/travel-requests/${id}/documents/upload`}
                        className="btn btn--secondary btn--sm"
                      >
                        Upload
                      </Link>
                    ) : document.status === "VERIFIED" ? (
                      <span className="secondary">✓ Verified</span>
                    ) : (
                      <span className="secondary">Awaiting review</span>
                    )}
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        </Card>
      )}

      <p className="mt-3">
        <Button variant="ghost" size="sm" onClick={fetchTravelRequestDetails}>
          ↻ Refresh
        </Button>
      </p>
    </>
  );
}

export default TravelRequestDetails;
