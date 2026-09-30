import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import apiClient from "../api/client";

import { useAuth } from "../hooks/useAuth";
import WorkflowProgress from "../components/WorkflowProgress";
import DocumentsCard from "../components/DocumentsCard";
import TravelSections from "../components/TravelSections";
import {
  PageHeader,
  Breadcrumb,
  Card,
  Button,
  ConfirmationDialog,
  RequestStatusBadge,
  TravelTypeBadge,
  DocumentStatusBadge,
  LoadingState,
  ErrorState,
  InlineError,
  EmptyState,
} from "../components/ui";
import { formatDate, travelWindow } from "../lib/format";

function ManagerTravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [travelRequest, setTravelRequest] = useState(null);
  const [checklist, setChecklist] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);

  const [rejectionComments, setRejectionComments] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [showApproveConfirm, setShowApproveConfirm] = useState(false);

  const loadDetails = async () => {
    try {
      setLoading(true);
      setError("");

      const requestResponse = await apiClient.get(
        `travel-requests/${id}/`
      );

      const checklistResponse = await apiClient.get(
        `travel-requests/${id}/documents/`
      );

      setTravelRequest(requestResponse.data);

      const checklistData = checklistResponse.data;

      if (Array.isArray(checklistData)) {
        setChecklist(checklistData);
      } else if (Array.isArray(checklistData.checklist)) {
        setChecklist(checklistData.checklist);
      } else if (Array.isArray(checklistData.results)) {
        setChecklist(checklistData.results);
      } else {
        setChecklist([]);
      }
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to load travel request details.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void loadDetails();
  }, [id]);

  /*
   * Document verification summary
   */

  const totalDocuments = checklist.length;

  const verifiedDocuments = checklist.filter(
    (document) => document.status === "VERIFIED"
  ).length;

  const pendingDocuments = checklist.filter(
    (document) =>
      document.status === "UPLOADED" ||
      document.status === "PENDING_REVIEW" ||
      document.status === "EXPIRING_SOON"
  ).length;

  const rejectedDocuments = checklist.filter(
    (document) => document.status === "REJECTED"
  ).length;

  const missingDocuments = checklist.filter(
    (document) => document.status === "MISSING"
  ).length;

  const mandatoryDocuments = checklist.filter(
    (document) => document.mandatory === true
  ).length;

  const verifiedMandatoryDocuments =
    checklist.filter(
      (document) =>
        document.mandatory === true &&
        document.status === "VERIFIED"
    ).length;

  const allMandatoryVerified =
    mandatoryDocuments === 0 ||
    verifiedMandatoryDocuments === mandatoryDocuments;

  /*
   * Manager approval
   */

  const approveTravelRequest = async () => {
    try {
      setProcessing(true);
      setError("");

      const response = await apiClient.post(
        `travel-requests/${id}/approve/`
      );

      setTravelRequest(response.data);
      setShowApproveConfirm(false);
    } catch (err) {
      setShowApproveConfirm(false);

      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to approve travel request.");
      }
    } finally {
      setProcessing(false);
    }
  };

  /*
   * Rejection
   */

  const rejectTravelRequest = async () => {
    if (!rejectionComments.trim()) {
      setError("Rejection comments are required.");
      return;
    }

    try {
      setProcessing(true);
      setError("");

      const response = await apiClient.post(
        `travel-requests/${id}/reject/`,
        {
          comments: rejectionComments.trim(),
        }
      );

      setTravelRequest(response.data);

      setShowRejectForm(false);
      setRejectionComments("");
    } catch (err) {
      if (err.response?.data?.comments) {
        setError(err.response.data.comments);
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to reject travel request.");
      }
    } finally {
      setProcessing(false);
    }
  };

  /*
   * Loading / error
   */

  if (loading) {
    return (
      <>
        <PageHeader
          title="Travel Request"
          description="Loading the request…"
        />
        <LoadingState label="Loading travel request…" />
      </>
    );
  }

  if (error && !travelRequest) {
    return (
      <>
        <Breadcrumb
          items={[
            { label: "Dashboard", to: "/dashboard" },
            { label: "Approval Queue", to: "/manager/travel-requests" },
            { label: `#${id}` },
          ]}
        />
        <ErrorState
          title="Unable to open this travel request"
          message={error}
        />
        <p className="mt-2">
          <Button
            variant="secondary"
            onClick={() => navigate("/manager/travel-requests")}
          >
            Back to Approval Queue
          </Button>
        </p>
      </>
    );
  }

  if (!travelRequest) {
    return null;
  }

  /*The manager decides while the request is in the
    MANAGER_APPROVAL stage (legacy requests keep the old
    DOCUMENT_VERIFICATION hand-off status).*/
  const canDecide =
    travelRequest.status === "MANAGER_APPROVAL" ||
    travelRequest.status === "DOCUMENT_VERIFICATION";

  return (
    <>
      <Breadcrumb
        items={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Approval Queue", to: "/manager/travel-requests" },
          { label: travelRequest.request_number || `#${id}` },
        ]}
      />

      <PageHeader
        title={`Request ${travelRequest.request_number || `#${id}`}`}
        description={`${travelRequest.employee_name || "Team member"} · ${
          travelRequest.destination_city || "—"
        } · ${travelWindow(travelRequest.start_date, travelRequest.end_date)}`}
        actions={
          <>
            <RequestStatusBadge status={travelRequest.status} />
            <TravelTypeBadge type={travelRequest.travel_type} />
          </>
        }
      />

      <InlineError>{error}</InlineError>

      {/* Decision panel */}
      {canDecide && (
        <Card
          title="Manager decision"
          subtitle="Review the request and document readiness, then approve or reject."
          className="mb-3"
        >
          <div className="btn-row">
            <Button
              onClick={() => setShowApproveConfirm(true)}
              disabled={processing}
            >
              Approve Travel Request
            </Button>

            <Button
              variant="danger-outline"
              onClick={() => {
                setError("");
                setRejectionComments("");
                setShowRejectForm(true);
              }}
              disabled={processing}
            >
              Reject Travel Request
            </Button>
          </div>
        </Card>
      )}

      {/* Rejection dialog */}
      {showRejectForm && (
        <ConfirmationDialog
          title="Reject Travel Request"
          message="Please provide a reason for rejecting this travel request. The employee will see this comment."
          confirmLabel="Confirm Rejection"
          danger
          busy={processing}
          onConfirm={rejectTravelRequest}
          onCancel={() => {
            setShowRejectForm(false);
            setRejectionComments("");
          }}
        >
          <textarea
            className="textarea"
            value={rejectionComments}
            onChange={(event) => setRejectionComments(event.target.value)}
            placeholder="Enter the reason for rejection…"
            rows={4}
            disabled={processing}
            aria-label="Rejection comments"
          />
        </ConfirmationDialog>
      )}

      {/* Approve confirmation */}
      {showApproveConfirm && (
        <ConfirmationDialog
          title="Approve Travel Request"
          message="Approve this travel request? The workflow will continue to the next stage."
          confirmLabel="Approve Request"
          busy={processing}
          onConfirm={approveTravelRequest}
          onCancel={() => setShowApproveConfirm(false)}
        />
      )}

      {/* Request information */}
      <Card title="Travel request information" className="mb-3">
        <div className="meta-list">
          <div>
            <div className="meta-item-label">Request Number</div>
            <div className="meta-item-value mono">
              {travelRequest.request_number || "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Employee</div>
            <div className="meta-item-value">
              {travelRequest.employee_name || "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Destination Country</div>
            <div className="meta-item-value">
              {travelRequest.country_name ||
                travelRequest.destination_country ||
                "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Destination City</div>
            <div className="meta-item-value">
              {travelRequest.destination_city || "—"}
            </div>
          </div>

          <div>
            <div className="meta-item-label">Travel Type</div>
            <div className="meta-item-value">
              <TravelTypeBadge type={travelRequest.travel_type} />
            </div>
          </div>

          <div>
            <div className="meta-item-label">Start Date</div>
            <div className="meta-item-value">
              {formatDate(travelRequest.start_date)}
            </div>
          </div>

          <div>
            <div className="meta-item-label">End Date</div>
            <div className="meta-item-value">
              {formatDate(travelRequest.end_date)}
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
            <div className="meta-item-label">Status</div>
            <div className="meta-item-value">
              <RequestStatusBadge status={travelRequest.status} />
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

      {/* Workflow + guidance, then documents, then the
          visa/booking/expense/settlement sections. */}
      <WorkflowProgress travelRequestId={id} />

      <DocumentsCard checklist={checklist} />

      <TravelSections
        travelRequestId={id}
        travelRequest={travelRequest}
        user={user}
      />

      {/* Document verification summary */}
      <Card
        title="Document verification summary"
        className="mb-3"
      >
        <div
          className={`alert ${
            allMandatoryVerified ? "alert--success" : "alert--warning"
          }`}
        >
          <span>
            {allMandatoryVerified
              ? "All mandatory documents are verified."
              : "All mandatory documents are not yet verified."}
          </span>
        </div>

        <div className="kpi-grid" style={{ marginBottom: 0 }}>
          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Total Documents</div>
            <div className="kpi-value">{totalDocuments}</div>
          </div>

          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Verified</div>
            <div className="kpi-value kpi-value--success">
              {verifiedDocuments}
            </div>
          </div>

          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Pending Review</div>
            <div className="kpi-value kpi-value--warning">
              {pendingDocuments}
            </div>
          </div>

          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Rejected</div>
            <div className="kpi-value kpi-value--danger">
              {rejectedDocuments}
            </div>
          </div>

          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Missing</div>
            <div className="kpi-value kpi-value--danger">
              {missingDocuments}
            </div>
          </div>
        </div>
      </Card>

      {/* Document status table */}
      <Card title="Document status" className="mb-3" padded={false}>
        {checklist.length === 0 ? (
          <EmptyState
            icon="📄"
            title="No document requirements found"
            description="This request does not require any documents."
          />
        ) : (
          <div className="table-wrap" style={{ border: "none", boxShadow: "none" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Required</th>
                  <th>Status</th>
                  <th>Issue Date</th>
                  <th>Expiry Date</th>
                </tr>
              </thead>

              <tbody>
                {checklist.map((document) => (
                  <tr key={document.document_type_id}>
                    <td className="cell-strong">{document.document_type}</td>

                    <td>{document.mandatory ? "Yes" : "No"}</td>

                    <td>
                      <DocumentStatusBadge status={document.status} />
                    </td>

                    <td>{formatDate(document.issue_date)}</td>

                    <td>{formatDate(document.expiry_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <p className="mt-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/manager/travel-requests")}
        >
          ← Back to Approval Queue
        </Button>
      </p>
    </>
  );
}

export default ManagerTravelRequestDetails;
