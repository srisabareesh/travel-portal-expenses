/**
 * Shared formatting + status helpers.
 *
 * The backend remains the source of truth for statuses; these maps only
 * translate backend enum values into human-readable labels and badge
 * variants. No logic lives here.
 */

/* ------------------------------------------------------------------ */
/* Request statuses                                                    */
/* ------------------------------------------------------------------ */

export const REQUEST_STATUS_LABELS = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  DOCUMENT_PENDING: "Documents Pending",
  DOCUMENTS_PENDING: "Documents Pending",
  DOCUMENTS_UNDER_REVIEW: "Documents Under Review",
  DOCUMENT_VERIFICATION: "Document Verification",
  MANAGER_APPROVAL: "Manager Approval",
  MANAGER_APPROVED: "Manager Approved",
  VISA_PROCESSING: "Visa Processing",
  VISA_APPROVED: "Visa Approved",
  TRAVEL_BOOKING: "Travel Booking",
  TRAVEL_BOOKED: "Travel Booked",
  TRAVEL_IN_PROGRESS: "Travel In Progress",
  EXPENSE_SUBMISSION: "Expense Submission",
  EXPENSE_VERIFICATION: "Expense Verification",
  SETTLEMENT_PENDING: "Settlement Pending",
  SETTLEMENT_APPROVAL: "Settlement Approval",
  SETTLEMENT_APPROVED: "Settlement Approved",
  SETTLEMENT_PROCESSING: "Settlement Processing",
  COMPLETED: "Completed",
  CLOSED: "Closed",
  REQUEST_REJECTED: "Request Rejected",
  REQUEST_CANCELLED: "Request Cancelled",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
};

/* Statuses that read as "in progress" for a reviewer/admin eye */
const PRIMARY_STATUSES = new Set([
  "SUBMITTED",
  "DOCUMENTS_PENDING",
  "DOCUMENT_PENDING",
  "DOCUMENTS_UNDER_REVIEW",
  "DOCUMENT_VERIFICATION",
  "MANAGER_APPROVAL",
  "MANAGER_APPROVED",
  "VISA_PROCESSING",
  "TRAVEL_BOOKING",
  "EXPENSE_SUBMISSION",
  "EXPENSE_VERIFICATION",
  "SETTLEMENT_APPROVAL",
  "SETTLEMENT_PROCESSING",
]);

const SUCCESS_STATUSES = new Set([
  "APPROVED",
  "MANAGER_APPROVED",
  "VISA_APPROVED",
  "TRAVEL_BOOKED",
  "COMPLETED",
  "CLOSED",
  "SETTLEMENT_APPROVED",
]);

const WARNING_STATUSES = new Set([
  "DRAFT",
  "EXPENSE_SUBMISSION",
  "SETTLEMENT_PENDING",
]);

const DANGER_STATUSES = new Set([
  "REJECTED",
  "REQUEST_REJECTED",
  "REQUEST_CANCELLED",
]);

export function requestStatusLabel(status) {
  return REQUEST_STATUS_LABELS[status] || status || "—";
}

export function requestStatusVariant(status) {
  if (DANGER_STATUSES.has(status)) return "danger";
  if (SUCCESS_STATUSES.has(status)) return "success";
  if (WARNING_STATUSES.has(status)) return "warning";
  if (PRIMARY_STATUSES.has(status)) return "primary";
  return "neutral";
}

/* ------------------------------------------------------------------ */
/* Document statuses                                                   */
/* ------------------------------------------------------------------ */

export const DOCUMENT_STATUS_LABELS = {
  MISSING: "Missing",
  UPLOADED: "Uploaded",
  PENDING_REVIEW: "Pending Review",
  VERIFIED: "Verified",
  REJECTED: "Rejected",
  EXPIRED: "Expired",
  EXPIRING_SOON: "Expiring Soon",
};

export function documentStatusLabel(status) {
  return DOCUMENT_STATUS_LABELS[status] || status || "—";
}

export function documentStatusVariant(status) {
  if (status === "VERIFIED") return "success";
  if (
    status === "MISSING" ||
    status === "REJECTED" ||
    status === "EXPIRED"
  ) {
    return "danger";
  }
  if (
    status === "PENDING_REVIEW" ||
    status === "UPLOADED" ||
    status === "EXPIRING_SOON"
  ) {
    return "warning";
  }
  return "neutral";
}

/* ------------------------------------------------------------------ */
/* Travel type & roles                                                 */
/* ------------------------------------------------------------------ */

export function travelTypeLabel(type) {
  if (type === "DOMESTIC") return "Domestic";
  if (type === "INTERNATIONAL") return "International";
  return type || "—";
}

export function roleLabel(role) {
  const labels = {
    EMPLOYEE: "Employee",
    REVIEWER: "Reviewer",
    MANAGER: "Manager",
    ADMIN: "Admin",
  };
  return labels[role] || role || "—";
}

/* ------------------------------------------------------------------ */
/* Dates & money                                                       */
/* ------------------------------------------------------------------ */

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Money formatting. No calculations — the backend supplies every number.
 */
export function formatMoney(value, currency) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return `${value}`.trim();
  }

  const formatted = number.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  return currency ? `${formatted} ${currency}` : formatted;
}

/* ------------------------------------------------------------------ */
/* Travel-window text                                                  */
/* ------------------------------------------------------------------ */

export function travelWindow(start, end) {
  if (!start && !end) return "—";
  if (!end || start === end) return formatDate(start);
  return `${formatDate(start)} – ${formatDate(end)}`;
}

/* ------------------------------------------------------------------ */
/* API error extraction — never show raw Axios output                  */
/* ------------------------------------------------------------------ */

export function extractApiError(error, fallback) {
  const data = error?.response?.data;

  if (typeof data === "string" && data.trim()) {
    return data;
  }

  if (data) {
    if (typeof data.detail === "string") return data.detail;

    const firstList = Object.values(data).find(
      (value) => Array.isArray(value) && value.length > 0
    );

    if (firstList) {
      return firstList.join(" ");
    }
  }

  return fallback || "Something went wrong. Please try again.";
}
