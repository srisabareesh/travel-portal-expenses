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
  Table,
  Modal,
  RequestStatusBadge,
  TravelTypeBadge,
  DocumentStatusBadge,
  LoadingState,
  ErrorState,
  InlineError,
  EmptyState,
} from "../components/ui";
import {
  formatDate,
  travelWindow,
  documentStatusLabel,
} from "../lib/format";

function ReviewerTravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [travelRequest, setTravelRequest] = useState(null);
  const [documents, setDocuments] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedDocument, setSelectedDocument] = useState(null);
  const [reviewComments, setReviewComments] = useState("");
  const [processing, setProcessing] = useState(false);

  const [verificationHistory, setVerificationHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  /* --------------------------------------------------
     Fetch Travel Request
     -------------------------------------------------- */

  const fetchTravelRequest = async () => {
    try {
      const response = await apiClient.get(
        `travel-requests/${id}/`
      );

      setTravelRequest(response.data);
    } catch (err) {
      if (err.response?.status === 403) {
        setError(
          "You do not have permission to access this travel request."
        );
      } else if (err.response?.status === 404) {
        setError("Travel request not found.");
      } else {
        setError("Unable to load travel request.");
      }
    }
  };

  /* --------------------------------------------------
     Fetch Documents
     -------------------------------------------------- */

  const fetchDocuments = async () => {
    try {
      const response = await apiClient.get(
        `travel-requests/${id}/documents/`
      );

      // Backend returns:
      // {
      //   checklist: [...],
      //   all_mandatory_verified: true/false
      // }
      setDocuments(response.data.checklist);
    } catch (err) {
      if (err.response?.status === 403) {
        setError(
          "You do not have permission to view these documents."
        );
      } else {
        setError("Unable to load travel documents.");
      }
    }
  };

  /* --------------------------------------------------
     Fetch Verification History
     -------------------------------------------------- */

  const fetchVerificationHistory = async (documentId) => {
    try {
      setHistoryLoading(true);

      const response = await apiClient.get(
        `documents/${documentId}/verification-history/`
      );

      setVerificationHistory(response.data);
    } catch (err) {
      setVerificationHistory([]);

      if (err.response?.status === 403) {
        setError(
          "You do not have permission to view verification history."
        );
      } else {
        setError("Unable to load verification history.");
      }
    } finally {
      setHistoryLoading(false);
    }
  };

  /* --------------------------------------------------
     Fetch All Data
     -------------------------------------------------- */

  const fetchData = async () => {
    setLoading(true);
    setError("");

    await Promise.all([
      fetchTravelRequest(),
      fetchDocuments(),
    ]);

    setLoading(false);
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void fetchData();
  }, [id]);

  /* --------------------------------------------------
     Open / Close Review
     -------------------------------------------------- */

  const openReview = async (document) => {
    setSelectedDocument(document);
    setReviewComments("");
    setVerificationHistory([]);
    setError("");

    await fetchVerificationHistory(
      document.document_id
    );
  };

  const closeReview = () => {
    setSelectedDocument(null);
    setReviewComments("");
    setVerificationHistory([]);
    setError("");
  };

  /* --------------------------------------------------
     Approve Document
     -------------------------------------------------- */

  const handleApprove = async () => {
    if (!selectedDocument) {
      return;
    }

    setProcessing(true);
    setError("");

    try {
      await apiClient.post(
        `documents/${selectedDocument.document_id}/verify/`,
        {
          status: "APPROVED",
          comments:
            reviewComments.trim() ||
            "Document verified successfully.",
        }
      );

      closeReview();

      await fetchData();
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Unable to approve the document.");
      }
    } finally {
      setProcessing(false);
    }
  };

  /* --------------------------------------------------
     Reject Document
     -------------------------------------------------- */

  const handleReject = async () => {
    if (!selectedDocument) {
      return;
    }

    if (!reviewComments.trim()) {
      setError(
        "Comments are required when rejecting a document."
      );
      return;
    }

    setProcessing(true);
    setError("");

    try {
      await apiClient.post(
        `documents/${selectedDocument.document_id}/verify/`,
        {
          status: "REJECTED",
          comments: reviewComments.trim(),
        }
      );

      closeReview();

      await fetchData();
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Unable to reject the document.");
      }
    } finally {
      setProcessing(false);
    }
  };

  /* --------------------------------------------------
     File URL Helper
     -------------------------------------------------- */

  const getFileUrl = (file) => {
    if (!file) {
      return null;
    }

    if (
      file.startsWith("http://") ||
      file.startsWith("https://")
    ) {
      return file;
    }

    const normalizedFile = file.startsWith("/")
      ? file
      : `/${file}`;

    return `http://127.0.0.1:8000${normalizedFile}`;
  };

  /* --------------------------------------------------
     Loading / Error
     -------------------------------------------------- */

  if (loading) {
    return (
      <>
        <PageHeader
          title="Review Travel Request"
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
            { label: "Review Queue", to: "/reviewer/travel-requests" },
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
            onClick={() => navigate("/reviewer/travel-requests")}
          >
            Back to Review Queue
          </Button>
        </p>
      </>
    );
  }

  if (!travelRequest) {
    return (
      <ErrorState
        title="Travel request not found"
        message="This request may have been removed."
      />
    );
  }

  /* --------------------------------------------------
     Review modal state
     -------------------------------------------------- */

  const reviewable =
    selectedDocument &&
    (selectedDocument.status === "UPLOADED" ||
      selectedDocument.status === "PENDING_REVIEW");

  /* --------------------------------------------------
     UI
     -------------------------------------------------- */

  return (
    <>
      <Breadcrumb
        items={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Review Queue", to: "/reviewer/travel-requests" },
          { label: travelRequest.request_number || `#${id}` },
        ]}
      />

      <PageHeader
        title={`Review ${travelRequest.request_number || `#${id}`}`}
        description={`${
          travelRequest.employee_name || "Employee"
        } · ${travelRequest.destination_city || "—"} · ${travelWindow(
          travelRequest.start_date,
          travelRequest.end_date
        )}`}
        actions={
          <>
            <RequestStatusBadge status={travelRequest.status} />
            <TravelTypeBadge type={travelRequest.travel_type} />
          </>
        }
      />

      <InlineError>{error}</InlineError>

      {/* Request summary */}
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
            <div className="meta-item-label">Destination</div>
            <div className="meta-item-value">
              {travelRequest.destination_city || "—"}
              {travelRequest.destination_country_name
                ? `, ${travelRequest.destination_country_name}`
                : travelRequest.country_name
                ? `, ${travelRequest.country_name}`
                : ""}
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
        </div>

        <div className="mt-2">
          <div className="meta-item-label">Purpose</div>
          <p className="meta-item-value mb-0" style={{ whiteSpace: "pre-wrap" }}>
            {travelRequest.purpose || "—"}
          </p>
        </div>
      </Card>

      {/* Workflow + guidance first, then documents, then
          the visa/booking/expense/settlement sections. */}
      <WorkflowProgress travelRequestId={id} />

      <DocumentsCard
        travelRequestId={id}
        checklist={documents}
      />

      <TravelSections
        travelRequestId={id}
        travelRequest={travelRequest}
        user={user}
      />

      {/* Reviewer verification workspace */}
      <Card
        title="Verify documents"
        subtitle="Open a document to review its contents and record your decision."
        className="mb-3"
        padded={false}
      >
        {documents.length === 0 ? (
          <EmptyState
            icon="📄"
            title="No documents found"
            description="The employee has not uploaded any documents yet."
          />
        ) : (
          <div className="table-wrap" style={{ border: "none", boxShadow: "none" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Document Type</th>
                  <th>Required</th>
                  <th>Status</th>
                  <th>Issue Date</th>
                  <th>Expiry Date</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>

              <tbody>
                {documents.map((document) => (
                  <tr key={document.document_id}>
                    <td className="cell-strong">
                      {document.document_type || "—"}
                    </td>

                    <td>{document.mandatory ? "Yes" : "No"}</td>

                    <td>
                      <DocumentStatusBadge status={document.status} />
                    </td>

                    <td>{formatDate(document.issue_date)}</td>

                    <td>{formatDate(document.expiry_date)}</td>

                    <td style={{ textAlign: "right" }}>
                      <div
                        className="btn-row"
                        style={{ justifyContent: "flex-end" }}
                      >
                        {document.file && (
                          <a
                            href={getFileUrl(document.file)}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn--ghost btn--sm"
                          >
                            View
                          </a>
                        )}

                        {document.status === "UPLOADED" ||
                        document.status === "PENDING_REVIEW" ? (
                          <Button size="sm" onClick={() => openReview(document)}>
                            Review
                          </Button>
                        ) : null}

                        {document.status === "REJECTED" ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openReview(document)}
                          >
                            View Review
                          </Button>
                        ) : null}

                        {document.status === "VERIFIED" ? (
                          <span className="secondary">✓ Verified</span>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Review modal */}
      {selectedDocument && (
        <Modal
          title={`Document Review — ${documentStatusLabel(
            selectedDocument.status
          )}`}
          onClose={closeReview}
        >
          <div className="meta-list mb-2">
            <div>
              <div className="meta-item-label">Document Type</div>
              <div className="meta-item-value">
                {selectedDocument.document_type || "—"}
              </div>
            </div>

            <div>
              <div className="meta-item-label">Status</div>
              <div className="meta-item-value">
                <DocumentStatusBadge status={selectedDocument.status} />
              </div>
            </div>
          </div>

          {selectedDocument.file && (
            <p>
              <a
                href={getFileUrl(selectedDocument.file)}
                target="_blank"
                rel="noreferrer"
                className="btn btn--secondary btn--sm"
              >
                Open Document
              </a>
            </p>
          )}

          <div className="form-field">
            <label htmlFor="review-comments">
              Review Comments
              {reviewable && (
                <span className="secondary"> (required when rejecting)</span>
              )}
            </label>

            <textarea
              id="review-comments"
              className="textarea"
              rows={4}
              value={reviewComments}
              onChange={(event) => setReviewComments(event.target.value)}
              placeholder="Enter review comments…"
              disabled={processing}
            />
          </div>

          {reviewable && (
            <div className="btn-row mt-2">
              <Button onClick={handleApprove} loading={processing}>
                Approve
              </Button>

              <Button
                variant="danger-outline"
                onClick={handleReject}
                disabled={processing}
              >
                Reject
              </Button>
            </div>
          )}

          {/* Verification history */}
          <hr className="divider" />

          <h3>Verification History</h3>

          {historyLoading ? (
            <LoadingState label="Loading verification history…" />
          ) : verificationHistory.length === 0 ? (
            <p className="secondary">No verification history found.</p>
          ) : (
            <Table
              compact
              columns={[
                { key: "reviewer", label: "Reviewer" },
                { key: "status", label: "Status" },
                { key: "at", label: "Verified At" },
                { key: "comments", label: "Comments" },
              ]}
            >
              {verificationHistory.map((verification) => (
                <tr key={verification.id}>
                  <td>
                    {verification.reviewer_name ||
                      verification.reviewer ||
                      "—"}
                  </td>

                  <td>
                    <DocumentStatusBadge status={verification.status} />
                  </td>

                  <td>{formatDate(verification.verified_at)}</td>

                  <td>{verification.comments || "—"}</td>
                </tr>
              ))}
            </Table>
          )}
        </Modal>
      )}

      <p className="mt-3 flex">
        <Button variant="ghost" size="sm" onClick={fetchData}>
          ↻ Refresh
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/reviewer/travel-requests")}
        >
          ← Back to Review Queue
        </Button>
      </p>
    </>
  );
}

export default ReviewerTravelRequestDetails;
