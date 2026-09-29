import { useEffect, useState } from "react";
import apiClient from "../api/client";

/**
 * WorkflowProgress — Phase 17.
 *
 * Renders the request lifecycle from the backend workflow
 * API. This component contains no workflow logic: it only
 * visualizes what the backend reports (stages, current
 * position, completed stages, allowed actions, exception
 * states). International stages are simply absent for
 * domestic requests because the backend workflow is
 * travel-type aware.
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



  if (error) {
    return <p style={{ color: "#c62828" }}>{error}</p>;
  }

  if (!progress) {
    return <p>Loading workflow progress…</p>;
  }

  const runAction = async (action) => {
    setBusyAction(action);
    setActionError("");

    try {
      await apiClient.post(
        `travel-requests/${travelRequestId}/${action}/`
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

  const {
    workflow,
    current_stage,
    completed_stages,
    pending_stage,
    is_exception,
    allowed_actions,
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
    is_exception && current_stage
      ? STAGE_LABELS[current_stage]
      : null;

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #ddd",
        borderRadius: "10px",
        padding: "20px",
        margin: "20px 0",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Workflow Progress</h3>

      <ol
        style={{
          listStyle: "none",
          display: "flex",
          flexWrap: "wrap",
          gap: "6px",
          padding: 0,
          margin: "12px 0",
        }}
      >
        {stageSequence.map((stage) => {
          const isCompleted = stage.statuses.every((s) =>
            completed_stages.includes(s)
          );

          const isCurrent =
            stage.statuses.includes(current_stage);

          const isException =
            exceptionStage === stage.group;

          let background = "#f2f2f2";
          let color = "#555";
          let border = "1px solid #ddd";

          if (isException) {
            background = "#ffebee";
            color = "#c62828";
            border = "1px solid #c62828";
          } else if (isCurrent) {
            background = "#e8f1ff";
            color = "#1d5fa7";
            border = "1px solid #1d5fa7";
          } else if (isCompleted) {
            background = "#e8f5e9";
            color = "#2e7d32";
          }

          return (
            <li
              key={stage.group}
              style={{
                background,
                color,
                border,
                padding: "6px 12px",
                borderRadius: "999px",
                fontWeight: isCurrent ? "bold" : "normal",
              }}
              title={stage.statuses.join(", ")}
            >
              {isCompleted && !isCurrent ? "✓ " : ""}
              {stage.group}
              {isCurrent ? " (current)" : ""}
            </li>
          );
        })}
      </ol>

      {pending_stage && !is_exception && (
        <p>
          <strong>Next:</strong>{" "}
          {STAGE_LABELS[pending_stage] || pending_stage}
        </p>
      )}

      {is_exception && current_stage && (
        <p
          style={{
            color: "#c62828",
            fontWeight: "bold",
          }}
        >
          This request is {STAGE_LABELS[current_stage] || current_stage}.
          No further actions are available.
        </p>
      )}

      {allowed_actions?.length > 0 && !is_exception && (
        <div
          style={{
            marginTop: "12px",
            display: "flex",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          {allowed_actions.map((action) => (
            <button
              key={action}
              onClick={() => runAction(action)}
              disabled={busyAction !== ""}
            >
              {busyAction === action
                ? "Working…"
                : ACTION_LABELS[action] || action}
            </button>
          ))}
        </div>
      )}

      {actionError && (
        <p style={{ color: "#c62828" }}>{actionError}</p>
      )}
    </div>
  );
}

export default WorkflowProgress;
