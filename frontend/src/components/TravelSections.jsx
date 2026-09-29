import { useCallback, useEffect, useState } from "react";
import apiClient from "../api/client";

import {
  Card,
  Button,
  Table,
  FormField,
  Modal,
  ConfirmationDialog,
  InlineError,
  Badge,
  EmptyState,
} from "./ui";
import { formatMoney, extractApiError } from "../lib/format";

/**
 * TravelSections — Phase 16.
 *
 * One implementation of the visa / booking / expense /
 * settlement sections, reused by the employee, reviewer
 * and manager detail pages. All mutations go through the
 * backend APIs; the backend enforces every permission, so
 * the UI simply renders the data and offers the actions
 * and shows backend errors when the backend refuses.
 */

const EXPENSE_CATEGORIES = [
  "FOOD",
  "HOTEL",
  "TRANSPORTATION",
  "VISA",
  "LOCAL_TRAVEL",
  "OTHER",
];

const EXPENSE_CATEGORY_LABELS = {
  FOOD: "Food",
  HOTEL: "Hotel",
  TRANSPORTATION: "Transportation",
  VISA: "Visa",
  LOCAL_TRAVEL: "Local Travel",
  OTHER: "Other",
};

const EXPENSE_STATUS_VARIANTS = {
  SUBMITTED: "warning",
  VERIFIED: "success",
  REJECTED: "danger",
};

const VISA_STATE_VARIANTS = {
  NOT_APPLIED: "neutral",
  APPLIED: "primary",
  UNDER_PROCESS: "warning",
  APPROVED: "success",
  REJECTED: "danger",
};

const VISA_STATE_LABELS = {
  NOT_APPLIED: "Not Applied",
  APPLIED: "Applied",
  UNDER_PROCESS: "Under Process",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

const BOOKING_STATUS_VARIANTS = {
  BOOKED: "success",
  CANCELLED: "danger",
  PENDING: "warning",
};

function SectionCard({ title, subtitle, actions, children }) {
  return (
    <Card title={title} subtitle={subtitle} actions={actions} className="mb-3">
      {children}
    </Card>
  );
}

export function TravelSections({ travelRequestId }) {
  const [visa, setVisa] = useState(null);
  const [flights, setFlights] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [config, setConfig] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [settlement, setSettlement] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);

  const [expenseForm, setExpenseForm] = useState({
    category: "FOOD",
    expense_date: "",
    amount: "",
    currency: "",
    description: "",
  });

  const [settlementForm, setSettlementForm] = useState({
    payment_date: "",
    payment_reference: "",
    payment_method: "",
    remarks: "",
  });

  const [rejectExpense, setRejectExpense] = useState(null);
  const [rejectComments, setRejectComments] = useState("");
  const [showProcessPayment, setShowProcessPayment] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoadError("");

    const safeGet = async (url, setter, missingOk) => {
      try {
        const response = await apiClient.get(url);

        setter(response.data);
      } catch (err) {
        if (err.response?.status === 404 && missingOk) {
          setter(null);
        } else if (err.response?.status === 400) {
          // e.g. visa on a domestic request: not applicable.
          setter(null);
        } else {
          setLoadError(
            "Some sections could not be loaded."
          );
        }
      }
    };

    await Promise.all([
      safeGet(
        `travel-requests/${travelRequestId}/visa/`,
        setVisa,
        true
      ),
      safeGet(
        `travel-requests/${travelRequestId}/bookings/flights/`,
        setFlights,
        false
      ),
      safeGet(
        `travel-requests/${travelRequestId}/bookings/hotels/`,
        setHotels,
        false
      ),
      safeGet(
        `travel-requests/${travelRequestId}/expense-configuration/`,
        setConfig,
        true
      ),
      safeGet(
        `travel-requests/${travelRequestId}/expenses/`,
        setExpenses,
        false
      ),
      safeGet(
        `travel-requests/${travelRequestId}/settlement/`,
        setSettlement,
        true
      ),
    ]);
  }, [travelRequestId]);

  const runAction = async (fn) => {
    setBusy(true);
    setActionError("");

    try {
      await fn();

      await fetchAll();
    } catch (err) {
      setActionError(
        extractApiError(err, "Action failed.")
      );
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void fetchAll();
  }, [travelRequestId]);

  // ---------- actions ----------

  const applyVisa = () =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/visa/apply/`,
        {
          applied_on: new Date()
            .toISOString()
            .slice(0, 10),
        }
      );
    });

  const decideVisa = (state) =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/visa/decision/`,
        { state }
      );
    });

  const addFlight = () =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/bookings/flights/`,
        { status: "BOOKED", booking_reference: "FL-" + Date.now() }
      );
    });

  const addHotel = () =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/bookings/hotels/`,
        { status: "BOOKED", booking_reference: "HT-" + Date.now() }
      );
    });

  const submitExpense = (event) => {
    event.preventDefault();

    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/expenses/`,
        expenseForm
      );

      setExpenseForm({
        category: "FOOD",
        expense_date: "",
        amount: "",
        currency: "",
        description: "",
      });
    });
  };

  const confirmRejectExpense = () => {
    if (!rejectExpense) {
      return;
    }

    if (!rejectComments.trim()) {
      return;
    }

    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/expenses/${rejectExpense.id}/verify/`,
        {
          status: "REJECTED",
          review_comments: rejectComments.trim(),
        }
      );

      setRejectExpense(null);
      setRejectComments("");
    });
  };

  const verifyExpense = (expenseId, decision) =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/expenses/${expenseId}/verify/`,
        { status: decision }
      );
    });

  const calculateSettlement = () =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/settlement/calculate/`
      );
    });

  const settlementAction = (action) =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/settlement/${action}/`,
        action === "start-processing"
          ? settlementForm
          : {}
      );
    });

  // ---------- rendering ----------

  const totalExpenses = expenses
    .filter((expense) => expense.status !== "REJECTED")
    .reduce(
      (sum, expense) => sum + Number(expense.amount || 0),
      0
    );

  return (
    <div>
      <InlineError>{loadError}</InlineError>

      {/* ---------------- Visa (international only; hidden otherwise) ---------------- */}
      {visa && (
        <SectionCard
          title="Visa"
          subtitle="Visa processing status for this international trip."
          actions={
            <Badge variant={VISA_STATE_VARIANTS[visa.state] || "neutral"}>
              {VISA_STATE_LABELS[visa.state] || visa.state}
            </Badge>
          }
        >
          <div className="meta-list">
            {visa.country && (
              <div>
                <div className="meta-item-label">Country</div>
                <div className="meta-item-value">{visa.country}</div>
              </div>
            )}

            {visa.applied_on && (
              <div>
                <div className="meta-item-label">Applied on</div>
                <div className="meta-item-value">{visa.applied_on}</div>
              </div>
            )}

            {visa.remarks && (
              <div>
                <div className="meta-item-label">Remarks</div>
                <div className="meta-item-value">{visa.remarks}</div>
              </div>
            )}
          </div>

          {["NOT_APPLIED", "REJECTED"].includes(visa.state) && (
            <div className="btn-row mt-2">
              <Button onClick={applyVisa} disabled={busy} loading={busy}>
                Apply for Visa
              </Button>
            </div>
          )}

          {["APPLIED", "UNDER_PROCESS"].includes(visa.state) && (
            <div className="btn-row mt-2">
              <Button onClick={() => decideVisa("APPROVED")} disabled={busy}>
                Mark Approved
              </Button>

              <Button
                variant="danger-outline"
                onClick={() => decideVisa("REJECTED")}
                disabled={busy}
              >
                Mark Rejected
              </Button>

              <Button
                variant="secondary"
                onClick={() => decideVisa("UNDER_PROCESS")}
                disabled={busy}
              >
                Mark Under Process
              </Button>
            </div>
          )}
        </SectionCard>
      )}

      {/* ---------------- Bookings ---------------- */}
      <SectionCard
        title="Flight booking"
        subtitle="Recorded flight bookings for this trip."
        actions={
          <Button variant="secondary" size="sm" onClick={addFlight} disabled={busy}>
            Record Flight Booking
          </Button>
        }
      >
        {flights.length === 0 ? (
          <p className="secondary mb-0">No flight bookings recorded yet.</p>
        ) : (
          <Table
            compact
            columns={[
              { key: "airline", label: "Airline / Flight" },
              { key: "reference", label: "Reference" },
              { key: "status", label: "Status" },
            ]}
          >
            {flights.map((flight) => (
              <tr key={flight.id}>
                <td className="cell-strong">
                  {flight.airline || "Airline TBD"}{" "}
                  {flight.flight_number}
                </td>

                <td className="mono">{flight.booking_reference}</td>

                <td>
                  <Badge variant={BOOKING_STATUS_VARIANTS[flight.status] || "neutral"}>
                    {flight.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </SectionCard>

      <SectionCard
        title="Hotel booking"
        subtitle="Recorded hotel bookings for this trip."
        actions={
          <Button variant="secondary" size="sm" onClick={addHotel} disabled={busy}>
            Record Hotel Booking
          </Button>
        }
      >
        {hotels.length === 0 ? (
          <p className="secondary mb-0">No hotel bookings recorded yet.</p>
        ) : (
          <Table
            compact
            columns={[
              { key: "hotel", label: "Hotel" },
              { key: "reference", label: "Reference" },
              { key: "status", label: "Status" },
            ]}
          >
            {hotels.map((hotel) => (
              <tr key={hotel.id}>
                <td className="cell-strong">
                  {hotel.hotel_name || "Hotel TBD"}
                </td>

                <td className="mono">{hotel.booking_reference}</td>

                <td>
                  <Badge variant={BOOKING_STATUS_VARIANTS[hotel.status] || "neutral"}>
                    {hotel.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </SectionCard>

      {/* -------- Expense configuration -------- */}
      {config && (
        <SectionCard
          title="Expense limits"
          subtitle="Approved limits for this trip, as configured by the travel desk."
        >
          <div className="kpi-grid" style={{ marginBottom: 0 }}>
            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Approved Limit</div>
              <div className="kpi-value">
                {formatMoney(
                  config.max_approved_expenses,
                  config.currency
                )}
              </div>
            </div>

            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Advance Given</div>
              <div className="kpi-value">
                {formatMoney(config.advance_amount, config.currency)}
              </div>
              <div className="kpi-hint">
                {config.advance_paid ? "Paid" : "Not paid"}
              </div>
            </div>

            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Daily Allowance</div>
              <div className="kpi-value">
                {formatMoney(config.daily_allowance, config.currency)}
              </div>
            </div>

            <div className="kpi" style={{ boxShadow: "none" }}>
              <div className="kpi-label">Expenses So Far</div>
              <div className="kpi-value kpi-value--primary">
                {formatMoney(totalExpenses, config.currency)}
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {/* ---------------- Expenses ---------------- */}
      <SectionCard
        title="Expenses"
        subtitle="Expenses claimed for this trip."
      >
        {expenses.length === 0 ? (
          <EmptyState
            icon="🧾"
            title="No expenses submitted"
            description="Add your first expense using the form below."
          />
        ) : (
          <>
            <Table
              columns={[
                { key: "date", label: "Date" },
                { key: "category", label: "Category" },
                { key: "amount", label: "Amount" },
                { key: "status", label: "Status" },
                { key: "actions", label: "Actions", align: "right" },
              ]}
            >
              {expenses.map((expense) => (
                <tr key={expense.id}>
                  <td>{expense.expense_date}</td>

                  <td>
                    <div className="cell-strong">
                      {EXPENSE_CATEGORY_LABELS[expense.category] ||
                        expense.category}
                    </div>

                    {expense.description && (
                      <div className="cell-secondary">
                        {expense.description}
                      </div>
                    )}
                  </td>

                  <td className="cell-strong">
                    {formatMoney(expense.amount, expense.currency)}
                  </td>

                  <td>
                    <Badge
                      variant={
                        EXPENSE_STATUS_VARIANTS[expense.status] || "neutral"
                      }
                    >
                      {expense.status === "SUBMITTED"
                        ? "Pending Review"
                        : expense.status === "VERIFIED"
                        ? "Verified"
                        : expense.status === "REJECTED"
                        ? "Rejected"
                        : expense.status}
                    </Badge>
                  </td>

                  <td style={{ textAlign: "right" }}>
                    {expense.status === "SUBMITTED" && (
                      <div
                        className="btn-row"
                        style={{ justifyContent: "flex-end" }}
                      >
                        <Button
                          size="sm"
                          onClick={() => verifyExpense(expense.id, "VERIFIED")}
                          disabled={busy}
                        >
                          Verify
                        </Button>

                        <Button
                          variant="danger-outline"
                          size="sm"
                          onClick={() => {
                            setRejectExpense(expense);
                            setRejectComments("");
                          }}
                          disabled={busy}
                        >
                          Reject
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </Table>

            <p className="mt-1 mb-0 secondary">
              Total (excluding rejected):{" "}
              <strong>
                {formatMoney(
                  totalExpenses,
                  expenses[0]?.currency || config?.currency
                )}
              </strong>
            </p>
          </>
        )}

        <hr className="divider" />

        <h3>Add expense</h3>

        <form onSubmit={submitExpense}>
          <div className="form-grid">
            <FormField label="Category" htmlFor="expense-category" required>
              <select
                id="expense-category"
                className="select"
                value={expenseForm.category}
                onChange={(event) =>
                  setExpenseForm({
                    ...expenseForm,
                    category: event.target.value,
                  })
                }
              >
                {EXPENSE_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {EXPENSE_CATEGORY_LABELS[category] || category}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Date" htmlFor="expense-date" required>
              <input
                id="expense-date"
                className="input"
                type="date"
                required
                value={expenseForm.expense_date}
                onChange={(event) =>
                  setExpenseForm({
                    ...expenseForm,
                    expense_date: event.target.value,
                  })
                }
              />
            </FormField>

            <FormField label="Amount" htmlFor="expense-amount" required>
              <input
                id="expense-amount"
                className="input"
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="0.00"
                value={expenseForm.amount}
                onChange={(event) =>
                  setExpenseForm({
                    ...expenseForm,
                    amount: event.target.value,
                  })
                }
              />
            </FormField>

            <FormField
              label="Currency (optional)"
              htmlFor="expense-currency"
              help="3-letter code, e.g. INR."
            >
              <input
                id="expense-currency"
                className="input"
                type="text"
                maxLength={3}
                placeholder="INR"
                value={expenseForm.currency}
                onChange={(event) =>
                  setExpenseForm({
                    ...expenseForm,
                    currency: event.target.value.toUpperCase(),
                  })
                }
              />
            </FormField>

            <div className="form-field--full">
              <FormField label="Description (optional)" htmlFor="expense-description">
                <input
                  id="expense-description"
                  className="input"
                  type="text"
                  placeholder="What was this expense for?"
                  value={expenseForm.description}
                  onChange={(event) =>
                    setExpenseForm({
                      ...expenseForm,
                      description: event.target.value,
                    })
                  }
                />
              </FormField>
            </div>
          </div>

          <div className="btn-row mt-2">
            <Button type="submit" disabled={busy} loading={busy}>
              Add Expense
            </Button>
          </div>
        </form>
      </SectionCard>

      {/* ---------------- Settlement ---------------- */}
      <SectionCard
        title="Settlement"
        subtitle="Final expense settlement for this trip."
      >
        {!settlement ? (
          <EmptyState
            icon="💰"
            title="Settlement not calculated yet"
            description="The settlement becomes available after expenses are verified and the workflow reaches settlement."
          />
        ) : (
          <>
            <div className="kpi-grid" style={{ marginBottom: 0 }}>
              <div className="kpi" style={{ boxShadow: "none" }}>
                <div className="kpi-label">Eligible Expenses</div>
                <div className="kpi-value">
                  {formatMoney(
                    settlement.eligible_expenses_total,
                    settlement.currency
                  )}
                </div>
              </div>

              <div className="kpi" style={{ boxShadow: "none" }}>
                <div className="kpi-label">Rejected Expenses</div>
                <div className="kpi-value kpi-value--danger">
                  {formatMoney(
                    settlement.rejected_expenses_total,
                    settlement.currency
                  )}
                </div>
              </div>

              <div className="kpi" style={{ boxShadow: "none" }}>
                <div className="kpi-label">Allowances</div>
                <div className="kpi-value">
                  {formatMoney(
                    settlement.allowances_total,
                    settlement.currency
                  )}
                </div>
              </div>

              <div className="kpi" style={{ boxShadow: "none" }}>
                <div className="kpi-label">Advance Paid</div>
                <div className="kpi-value">
                  {formatMoney(
                    settlement.advance_paid,
                    settlement.currency
                  )}
                </div>
              </div>

              <div className="kpi" style={{ boxShadow: "none" }}>
                <div className="kpi-label">Net Settlement</div>
                <div
                  className={`kpi-value ${
                    Number(settlement.net_settlement) < 0
                      ? "kpi-value--danger"
                      : "kpi-value--success"
                  }`}
                >
                  {formatMoney(
                    settlement.net_settlement,
                    settlement.currency
                  )}
                </div>

                <div className="kpi-hint">
                  {Number(settlement.net_settlement) < 0
                    ? "Employee owes company"
                    : Number(settlement.net_settlement) > 0
                    ? "Company owes employee"
                    : "Nothing due"}
                </div>
              </div>
            </div>

            <p className="mt-2 mb-0">
              <Badge
                variant={
                  settlement.status === "COMPLETED" || settlement.status === "APPROVED"
                    ? "success"
                    : settlement.status === "PENDING"
                    ? "neutral"
                    : "primary"
                }
              >
                Settlement status: {settlement.status}
              </Badge>
            </p>
          </>
        )}

        <div className="btn-row mt-2">
          <Button
            variant="secondary"
            onClick={calculateSettlement}
            disabled={busy}
            loading={busy}
          >
            Calculate Settlement
          </Button>

          {settlement?.status === "PENDING" && (
            <Button
              onClick={() => settlementAction("start-approval")}
              disabled={busy}
            >
              Send for Approval
            </Button>
          )}

          {settlement?.status === "IN_APPROVAL" && (
            <Button
              onClick={() => settlementAction("approve")}
              disabled={busy}
            >
              Approve Settlement
            </Button>
          )}

          {settlement?.status === "APPROVED" && (
            <Button onClick={() => setShowProcessPayment(true)} disabled={busy}>
              Process Payment
            </Button>
          )}

          {settlement?.status === "COMPLETED" && (
            <span className="secondary">Settlement completed.</span>
          )}
        </div>
      </SectionCard>

      {/* Process payment modal */}
      {showProcessPayment && settlement?.status === "APPROVED" && (
        <Modal
          title="Process Settlement Payment"
          onClose={() => setShowProcessPayment(false)}
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setShowProcessPayment(false)}
                disabled={busy}
              >
                Cancel
              </Button>

              <Button
                onClick={() => {
                  settlementAction("start-processing");
                  setShowProcessPayment(false);
                }}
                disabled={busy}
                loading={busy}
              >
                Process Settlement
              </Button>
            </>
          }
        >
          <div className="stack-sm">
            <FormField label="Payment Date" htmlFor="payment-date">
              <input
                id="payment-date"
                className="input"
                type="date"
                value={settlementForm.payment_date}
                onChange={(event) =>
                  setSettlementForm({
                    ...settlementForm,
                    payment_date: event.target.value,
                  })
                }
              />
            </FormField>

            <FormField label="Payment Reference" htmlFor="payment-reference">
              <input
                id="payment-reference"
                className="input"
                type="text"
                placeholder="e.g. NEFT-123456"
                value={settlementForm.payment_reference}
                onChange={(event) =>
                  setSettlementForm({
                    ...settlementForm,
                    payment_reference: event.target.value,
                  })
                }
              />
            </FormField>

            <FormField label="Payment Method" htmlFor="payment-method">
              <input
                id="payment-method"
                className="input"
                type="text"
                placeholder="e.g. Bank Transfer"
                value={settlementForm.payment_method}
                onChange={(event) =>
                  setSettlementForm({
                    ...settlementForm,
                    payment_method: event.target.value,
                  })
                }
              />
            </FormField>
          </div>
        </Modal>
      )}

      {/* Expense rejection dialog */}
      {rejectExpense && (
        <ConfirmationDialog
          title="Reject Expense"
          message={`Reject this ${EXPENSE_CATEGORY_LABELS[rejectExpense.category] || rejectExpense.category} expense of ${formatMoney(rejectExpense.amount, rejectExpense.currency)}? A reason is required.`}
          confirmLabel="Confirm Rejection"
          danger
          busy={busy}
          onConfirm={confirmRejectExpense}
          onCancel={() => {
            setRejectExpense(null);
            setRejectComments("");
          }}
        >
          <textarea
            className="textarea"
            rows={3}
            value={rejectComments}
            onChange={(event) => setRejectComments(event.target.value)}
            placeholder="Reason for rejecting this expense…"
            aria-label="Expense rejection comments"
          />
        </ConfirmationDialog>
      )}

      <InlineError>{actionError}</InlineError>
    </div>
  );
}

export default TravelSections;
