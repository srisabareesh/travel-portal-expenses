import { Link } from "react-router-dom";

import { Card, Table, DocumentStatusBadge } from "./ui";
import { formatDate } from "../lib/format";

/**
 * DocumentsCard — Phase 21/23.
 *
 * One implementation of the document checklist card,
 * placed directly after Workflow Progress on every detail
 * page. Renders the backend-provided checklist; upload
 * actions appear only for the employee who owns the
 * request while the request is inside its document
 * workflow (the backend enforces this independently).
 */

export default function DocumentsCard({
  checklist = [],
  uploadBaseUrl,
  canUpload = true,
}) {
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
      ? Math.round(
          (verifiedDocuments / totalDocuments) * 100
        )
      : 0;

  const needsDocumentAction =
    canUpload &&
    checklist.some(
      (document) =>
        document.status === "MISSING" ||
        document.status === "REJECTED"
    );

  const canUploadDocument =
    canUpload && uploadBaseUrl;

  if (totalDocuments === 0) {
    return null;
  }

  return (
    <Card
      title="Documents"
      subtitle={
        needsDocumentAction
          ? "Some documents are missing or were rejected — upload them to continue."
          : `${verifiedDocuments} of ${totalDocuments} documents verified.`
      }
      className="mb-3"
      actions={
        needsDocumentAction && canUploadDocument ? (
          <Link
            to={uploadBaseUrl}
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
        <span className="secondary">
          {completionPercentage}%
        </span>
      </div>

      <div
        className="progress"
        role="progressbar"
        aria-valuenow={completionPercentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Document verification progress"
      >
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
                {canUploadDocument &&
                (document.status === "MISSING" ||
                  document.status === "REJECTED") ? (
                  <Link
                    to={uploadBaseUrl}
                    className="btn btn--secondary btn--sm"
                  >
                    Upload
                  </Link>
                ) : document.status === "VERIFIED" ? (
                  <span className="secondary">✓ Verified</span>
                ) : (
                  <span className="secondary">
                    Awaiting review
                  </span>
                )}
              </td>
            </tr>
          ))}
        </Table>
      </div>
    </Card>
  );
}
