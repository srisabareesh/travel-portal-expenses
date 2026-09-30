import { useEffect, useState } from "react";
import apiClient from "../api/client";
import { Card, Button, Badge } from "./ui";
import { requestStatusLabel } from "../lib/format";

/**
 * WorkflowProgress — Phase 21.
 *
 * Renders the request lifecycle from the backend workflow
 * API. This component contains no workflow logic: it only
 * visualizes what the backend reports (stages, current
 * position, completed stages, next action, pending role,
 * role-filtered allowed actions, exception states).
 * International stages are simply absent for domestic
 * requests because the backend workflow is travel-type
 * aware.
 */

const STAGE_LABELS = {
  DRAFT: "Request",
  SUBMITTED: "Submitted",
  DOCUMENTS_PENDING: "Documents",
  DOCUMENTS_UNDER_REVIEW: "Documents",
  DOCUMENT_PENDING: "Documents",
  DOCUMENT_VERIFICATION: "Document Review",
  MANAGER_APPROVAL: "Manager Approval",
  MANAGER_APPROVED: "Approved",
  VISA_PROCESSING: "Visa",
  VISA_APPROVED: "Visa",
  TRAVEL_BOOKING: "Booking",
  TRAVEL_BOOKED: "Booking",
  TRAVEL_IN_PROGRESS: "Travel",
  EXPENSE_SUBMISSION: "Expenses",
  EXPENSE_VERIFICATION: "Verification",
  SETTLEMENT_PENDING: "Settlement",
  SETTLEMENT_APPROVAL: "Settlement",
  SETTLEMENT_APPROVED: "Settlement",
  SETTLEMENT_PROCESSING: "Settlement",
  COMPLETED: "Completed",
  CLOSED: "Closed",
  REQUEST_REJECTED: "Rejected",
  REQUEST_CANCELLED: "Cancelled",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
};

const ACTION_LABELS = {
  submit: "Submit Request",
  "start-review": "Start Document Review",
  "submit-for-approval": "Send for Manager Approval",
  approve: "Approve Request",
  reject: "Reject Request",
  cancel: "Cancel Request",
  "start-visa": "Start Visa Processing",
  "visa-decide": "Record Visa Decision",
  "start-booking": "Start Booking",
  "complete-booking": "Complete Booking",
  "start-travel": "Start Travel",
  "submit-expenses": "Submit Expenses",
  "start-expense-review": "Start Expense Review",
  settle: "Calculate Settlement",
  "start-settlement-approval": "Send Settlement for Approval",
  "approve-settlement": "Approve Settlement",
  "start-settlement-processing": "Process Settlement",
  complete: "Complete Request",
  close: "Close Request",
};

export function WorkflowProgress({
  travelRequestId,
  onChanged,
}) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [actionError, setActionError] = useState("");

  const fetchProgress = async () => {
    try {
      const response = await apiClient.get(
        `travel-requests/${travelRequestId}/workflow/`
      );

      setProgress(response.data);
      setError("");
    } catch {
      setError("Unable to load workflow progress.");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void fetchProgress();
  }, [travelRequestId]);

  const runAction = async (action) => {
    setBusyAction(action);
    setActionError("");

    try {
      // The workflow engine exposes POST endpoints at
      // <action-with-hyphens>/ (e.g. start-review/).
      const urlPath = String(action).replaceAll("_", "-");

      await apiClient.post(
        `travel-requests/${travelRequestId}/${urlPath}/`
      );

      await fetchProgress();

      if (onChanged) {
        onChanged();
      }
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.status?.[0] ||
        "Action failed.";

      setActionError(detail);
    } finally {
      setBusyAction("");
    }
  };

  if (error) {
    return (
      <div className="alert alert--error" role="alert">
        <span>{error}</span>
      </div>
    );
  }

  if (!progress) {
    return (
      <div className="card card-pad mb-3" role="status">
        <div className="spinner" aria-hidden="true" />
        <p className="secondary mb-0">Loading workflow progress…</p>
      </div>
    );
  }

  const {
    workflow,
    current_stage,
    current_status,
    completed_stages,
    pending_stage,
    is_exception,
    my_allowed_actions,
    next_action,
    pending_with,
  } = progress;

  // Group consecutive raw statuses into the friendly
  // business stages from the master specification.
  const stageSequence = [];
  let lastGroup = null;

  for (const status of workflow) {
    const group = STAGE_LABELS[status] || status;

    if (group !== lastGroup) {
      stageSequence.push({
        group,
        statuses: [status],
      });

      lastGroup = group;
    } else {
      stageSequence[stageSequence.length - 1].statuses.push(
        status
      );
    }
  }

  const exceptionStage =
    is_exception && current_status
      ? STAGE_LABELS[current_status] ||
        STAGE_LABELS[current_stage] ||
        current_status
      : null;

  return (
    <Card
      title="Workflow progress"
      className="mb-3"
      actions={
        pending_stage && !is_exception ? (
          <span className="secondary">
            Next:{" "}
            <strong>
              {STAGE_LABELS[pending_stage] || pending_stage}
            </strong>
          </span>
        ) : undefined
      }
    >
      <ol
        className="workflow"
        style={{ listStyle: "none", padding: 0, margin: "8px 0 0" }}
      >
        {stageSequence.map((stage) => {
          const isCompleted = stage.statuses.every((s) =>
            completed_stages.includes(s)
          );

          const isCurrent =
            stage.statuses.includes(current_stage);

          const isException =
            exceptionStage === stage.group;

          const stepClass = isException
            ? "exception"
            : isCurrent
            ? "current"
            : isCompleted
            ? "done"
            : "";

          return (
            <li
              key={stage.group}
              className={`workflow-step ${stepClass}`.trim()}
              title={stage.statuses.join(", ")}
            >
              <div className="workflow-dot" aria-hidden="true">
                {isCompleted && !isCurrent ? "✓" : ""}
              </div>

              <div className="workflow-label">
                {stage.group}
                {isCurrent ? " · current" : ""}
              </div>
            </li>
          );
        })}
      </ol>

      {/* Current status / next action / pending with — all
          values come from the backend workflow engine. */}
      {!is_exception && current_stage && (
        <div
          className="kpi-grid mt-2"
          style={{ marginBottom: 0 }}
        >
          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Current status</div>
            <div className="kpi-value" style={{ fontSize: "1rem" }}>
              {requestStatusLabel(current_status || current_stage)}
            </div>
          </div>

          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Next action</div>
            <div className="kpi-hint" style={{ fontSize: "0.95rem" }}>
              {next_action || "—"}
            </div>
          </div>

          <div className="kpi" style={{ boxShadow: "none" }}>
            <div className="kpi-label">Pending with</div>
            <div className="kpi-value" style={{ fontSize: "1rem" }}>
              {pending_with ? (
                <Badge variant="primary">{pending_with}</Badge>
              ) : (
                "—"
              )}
            </div>
          </div>
        </div>
      )}

      {is_exception && current_stage && (
        <div className="alert alert--error mt-2" role="status">
          <span>
            This request is{" "}
            {exceptionStage || current_stage}. No further
            actions are available.
          </span>
        </div>
      )}

      {my_allowed_actions?.length > 0 && !is_exception && (
        <div className="btn-row mt-2">
          {my_allowed_actions.map((action) => (
            <Button
              key={action}
              size="sm"
              onClick={() => runAction(action)}
              disabled={busyAction !== ""}
              loading={busyAction === action}
            >
              {busyAction === action
                ? "Working…"
                : ACTION_LABELS[action] || action}
            </Button>
          ))}
        </div>
      )}

      {actionError && (
        <div className="alert alert--error mt-2" role="alert">
          <span>{actionError}</span>
        </div>
      )}
    </Card>
  );
}

export default WorkflowProgress;
