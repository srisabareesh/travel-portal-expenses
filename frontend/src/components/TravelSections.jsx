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
import {
  formatDateTime,
  formatMoney,
  extractApiError,
  CURRENCIES,
} from "../lib/format";

/**
 * TravelSections — Phase 21.
 *
 * One implementation of the visa / booking / expense /
 * settlement sections, reused by the employee, reviewer
 * and manager detail pages.
 *
 * Phase 21 corrections:
 *   - the caller passes the travel request + the signed-in
 *     user so every action is role- AND stage-gated in the
 *     UI (the backend independently enforces everything);
 *   - visa actions are employee-only and appear only while
 *     the request is in VISA_PROCESSING;
 *   - booking forms are reviewer-only, in the booking
 *     stage, with real editable fields (no fake data);
 *   - the expense currency is a dropdown (centralized
 *     list), not free text;
 *   - the expense limits panel is editable by the reviewer
 *     at the booking/after-booking stage;
 *   - Calculate Settlement only renders at
 *     EXPENSE_VERIFICATION for reviewers, and once a
 *     settlement exists the calculated numbers are shown
 *     instead of the calculate button.
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

function roleFlags(user) {
  const roles = user?.roles || [];

  const has = (role) => roles.includes(role);

  return {
    isEmployee: has("EMPLOYEE"),
    isReviewer: has("REVIEWER"),
    isManager: has("MANAGER"),
    isAdmin: has("ADMIN"),
  };
}

export function TravelSections({ travelRequestId, travelRequest, user }) {
  const [visa, setVisa] = useState(null);
  const [flights, setFlights] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [config, setConfig] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [settlement, setSettlement] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);

  const [showFlightForm, setShowFlightForm] = useState(false);
  const [showHotelForm, setShowHotelForm] = useState(false);
  const [showLimitsForm, setShowLimitsForm] = useState(false);

  const [flightForm, setFlightForm] = useState({
    airline: "",
    flight_number: "",
    departure_date: "",
    departure_time: "",
    arrival_date: "",
    arrival_time: "",
    origin: "",
    destination: "",
    booking_reference: "",
    notes: "",
  });

  const [hotelForm, setHotelForm] = useState({
    hotel_name: "",
    address: "",
    check_in: "",
    check_out: "",
    booking_reference: "",
    notes: "",
  });

  const [limitsForm, setLimitsForm] = useState({
    max_approved_expenses: "",
    advance_amount: "",
    daily_allowance: "",
    currency: "INR",
  });

  const [expenseForm, setExpenseForm] = useState({
    category: "FOOD",
    expense_date: "",
    amount: "",
    currency: "INR",
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

  const { isReviewer, isManager } = roleFlags(user);
  const isOwner =
    user && travelRequest
      ? travelRequest.employee === user.id
      : false;

  // ---------------- role & stage gates ----------------

  const status = travelRequest?.status || "";

  const isInternational =
    travelRequest?.travel_type === "INTERNATIONAL";

  // Visa is international-only and belongs to the
  // employee while the request is in visa processing.
  const visaStageActive =
    isInternational && status === "VISA_PROCESSING";

  const canUpdateVisa = isOwner && visaStageActive;

  // Booking window (mirrors the backend gate): domestic
  // after manager approval; international only once the
  // visa is APPROVED. The reviewer may record bookings.
  const inBookingWindow =
    isReviewer &&
    (isInternational
      ? status === "VISA_APPROVED" || status === "TRAVEL_BOOKING"
      : status === "MANAGER_APPROVED" ||
        status === "TRAVEL_BOOKING");

  // Expense entry is the employee's own action while the
  // trip is in the expense stages (matching the backend
  // guard, which also allows late receipts during
  // EXPENSE_VERIFICATION).
  const canAddExpenses =
    isOwner &&
    (status === "TRAVEL_IN_PROGRESS" ||
      status === "EXPENSE_SUBMISSION" ||
      status === "EXPENSE_VERIFICATION");

  // Expense verify/reject is reviewer-only.
  const canVerifyExpenses = isReviewer;

  // Limits are configured by the reviewer after approval
  // and during the booking/travel stages.
  const canConfigureLimits =
    isReviewer &&
    [
      "MANAGER_APPROVED",
      "VISA_APPROVED",
      "TRAVEL_BOOKING",
      "TRAVEL_BOOKED",
      "TRAVEL_IN_PROGRESS",
      "EXPENSE_SUBMISSION",
      "EXPENSE_VERIFICATION",
    ].includes(status);

  // Settlement calculation: reviewer, exactly at
  // EXPENSE_VERIFICATION, when not calculated yet.
  const canCalculateSettlement =
    isReviewer &&
    status === "EXPENSE_VERIFICATION" &&
    !settlement;

  // Settlement lifecycle actions follow the settlement
  // record's own status, with the request's stage.
  const settlementLifecycle = settlement
    ? {
        canStartApproval:
          (isReviewer || isManager) &&
          settlement.status === "PENDING" &&
          status === "SETTLEMENT_PENDING",
        canApprove:
          isManager &&
          settlement.status === "IN_APPROVAL" &&
          status === "SETTLEMENT_APPROVAL" &&
          !isOwner,
        canProcess:
          (isReviewer || isManager) &&
          settlement.status === "APPROVED" &&
          status === "SETTLEMENT_APPROVED",
        canComplete:
          (isReviewer || isManager) &&
          settlement.status === "PROCESSING" &&
          status === "SETTLEMENT_PROCESSING",
      }
    : null;

  // ---------------- data loading ----------------

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
        } else if (err.response?.status === 403) {
          // Hidden from this role: treat as not available.
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

  // ---------------- actions ----------------

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

  const submitFlight = (event) => {
    event.preventDefault();

    const departure_datetime =
      flightForm.departure_date && flightForm.departure_time
        ? `${flightForm.departure_date}T${flightForm.departure_time}:00`
        : null;

    const arrival_datetime =
      flightForm.arrival_date && flightForm.arrival_time
        ? `${flightForm.arrival_date}T${flightForm.arrival_time}:00`
        : null;

    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/bookings/flights/`,
        {
          airline: flightForm.airline,
          flight_number: flightForm.flight_number,
          departure_datetime,
          arrival_datetime,
          origin: flightForm.origin,
          destination: flightForm.destination,
          booking_reference: flightForm.booking_reference,
          notes: flightForm.notes,
          status: "BOOKED",
        }
      );

      setShowFlightForm(false);
      setFlightForm({
        airline: "",
        flight_number: "",
        departure_date: "",
        departure_time: "",
        arrival_date: "",
        arrival_time: "",
        origin: "",
        destination: "",
        booking_reference: "",
        notes: "",
      });
    });
  };

  const submitHotel = (event) => {
    event.preventDefault();

    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/bookings/hotels/`,
        {
          hotel_name: hotelForm.hotel_name,
          address: hotelForm.address,
          check_in: hotelForm.check_in || null,
          check_out: hotelForm.check_out || null,
          booking_reference: hotelForm.booking_reference,
          notes: hotelForm.notes,
          status: "BOOKED",
        }
      );

      setShowHotelForm(false);
      setHotelForm({
        hotel_name: "",
        address: "",
        check_in: "",
        check_out: "",
        booking_reference: "",
        notes: "",
      });
    });
  };

  const submitLimits = (event) => {
    event.preventDefault();

    runAction(async () => {
      await apiClient.put(
        `travel-requests/${travelRequestId}/expense-configuration/`,
        {
          max_approved_expenses:
            limitsForm.max_approved_expenses || null,
          advance_amount: limitsForm.advance_amount || null,
          daily_allowance: limitsForm.daily_allowance || null,
          currency: limitsForm.currency,
        }
      );

      setShowLimitsForm(false);
    });
  };

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
        currency: "INR",
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

  // ---------------- derived display values ----------------

  const verifiedTotal = expenses
    .filter((expense) => expense.status === "VERIFIED")
    .reduce(
      (sum, expense) => sum + Number(expense.amount || 0),
      0
    );

  const displayCurrency =
    config?.currency || expenses[0]?.currency || "";

  const remainingBalance =
    config?.max_approved_expenses != null
      ? Number(config.max_approved_expenses) - verifiedTotal
      : null;

  return (
    <div>
      <InlineError>{loadError}</InlineError>

      {/* ---------------- Visa (international only) ---------------- */}
      {isInternational && visa && (
        <SectionCard
          title="Visa"
          subtitle={
            visaStageActive
              ? "The travelling employee updates the visa status; reviewer/HR and managers have read-only access."
              : "Visa processing status for this international trip."
          }
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

          {canUpdateVisa &&
            ["NOT_APPLIED", "REJECTED"].includes(visa.state) && (
              <div className="btn-row mt-2">
                <Button onClick={applyVisa} disabled={busy} loading={busy}>
                  I Have Applied
                </Button>
              </div>
            )}

          {canUpdateVisa &&
            ["APPLIED", "UNDER_PROCESS", "REJECTED"].includes(
              visa.state
            ) && (
              <div className="btn-row mt-2">
                {visa.state !== "APPLIED" && (
                  <Button
                    onClick={() => decideVisa("APPLIED")}
                    disabled={busy}
                  >
                    Mark Applied
                  </Button>
                )}

                <Button
                  onClick={() => decideVisa("UNDER_PROCESS")}
                  disabled={busy}
                >
                  Mark Under Process
                </Button>

                <Button
                  onClick={() => decideVisa("APPROVED")}
                  disabled={busy}
                >
                  Visa Approved
                </Button>

                <Button
                  variant="danger-outline"
                  onClick={() => decideVisa("REJECTED")}
                  disabled={busy}
                >
                  Visa Rejected
                </Button>
              </div>
            )}

          {!canUpdateVisa && !isOwner && visaStageActive && (
            <p className="secondary mt-1 mb-0">
              Visa status is updated by the travelling employee.
            </p>
          )}

          {isOwner && !visaStageActive && (
            <p className="secondary mt-1 mb-0">
              Visa updates open when the request reaches visa
              processing (after documents are verified and the
              manager approves).
            </p>
          )}
        </SectionCard>
      )}

      {/* ---------------- Flight booking ---------------- */}
      <SectionCard
        title="Flight booking"
        subtitle={
          isReviewer
            ? "Record the flight booking with the real travel details."
            : "Flight bookings recorded by the travel desk."
        }
        actions={
          inBookingWindow ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFlightForm(true)}
              disabled={busy}
            >
              Record Flight Booking
            </Button>
          ) : undefined
        }
      >
        {flights.length === 0 ? (
          <p className="secondary mb-0">
            Flight booking has not been recorded yet.
          </p>
        ) : (
          <div className="meta-list">
            {flights.map((flight) => (
              <div key={flight.id} className="stack-sm">
                <div className="flex-between">
                  <div className="cell-strong">
                    {flight.airline || "—"}
                    {flight.flight_number
                      ? ` · ${flight.flight_number}`
                      : ""}
                  </div>

                  <Badge
                    variant={
                      BOOKING_STATUS_VARIANTS[flight.status] ||
                      "neutral"
                    }
                  >
                    {flight.status}
                  </Badge>
                </div>

                <div className="meta-list">
                  {flight.origin && (
                    <div>
                      <div className="meta-item-label">From</div>
                      <div className="meta-item-value">
                        {flight.origin}
                      </div>
                    </div>
                  )}

                  {flight.destination && (
                    <div>
                      <div className="meta-item-label">To</div>
                      <div className="meta-item-value">
                        {flight.destination}
                      </div>
                    </div>
                  )}

                  {flight.departure_datetime && (
                    <div>
                      <div className="meta-item-label">Departure</div>
                      <div className="meta-item-value">
                        {formatDateTime(flight.departure_datetime)}
                      </div>
                    </div>
                  )}

                  {flight.arrival_datetime && (
                    <div>
                      <div className="meta-item-label">Arrival</div>
                      <div className="meta-item-value">
                        {formatDateTime(flight.arrival_datetime)}
                      </div>
                    </div>
                  )}

                  {flight.booking_reference && (
                    <div>
                      <div className="meta-item-label">Reference</div>
                      <div className="meta-item-value mono">
                        {flight.booking_reference}
                      </div>
                    </div>
                  )}

                  {flight.notes && (
                    <div>
                      <div className="meta-item-label">Notes</div>
                      <div className="meta-item-value">
                        {flight.notes}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {/* ---------------- Hotel booking ---------------- */}
      <SectionCard
        title="Hotel booking"
        subtitle={
          isReviewer
            ? "Record the hotel booking with the real stay details."
            : "Hotel bookings recorded by the travel desk."
        }
        actions={
          inBookingWindow ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowHotelForm(true)}
              disabled={busy}
            >
              Record Hotel Booking
            </Button>
          ) : undefined
        }
      >
        {hotels.length === 0 ? (
          <p className="secondary mb-0">
            Hotel booking has not been recorded yet.
          </p>
        ) : (
          <div className="meta-list">
            {hotels.map((hotel) => (
              <div key={hotel.id} className="stack-sm">
                <div className="flex-between">
                  <div className="cell-strong">
                    {hotel.hotel_name || "—"}
                  </div>

                  <Badge
                    variant={
                      BOOKING_STATUS_VARIANTS[hotel.status] ||
                      "neutral"
                    }
                  >
                    {hotel.status}
                  </Badge>
                </div>

                <div className="meta-list">
                  {hotel.address && (
                    <div>
                      <div className="meta-item-label">Address</div>
                      <div className="meta-item-value">
                        {hotel.address}
                      </div>
                    </div>
                  )}

                  {hotel.check_in && (
                    <div>
                      <div className="meta-item-label">Check-in</div>
                      <div className="meta-item-value">
                        {hotel.check_in}
                      </div>
                    </div>
                  )}

                  {hotel.check_out && (
                    <div>
                      <div className="meta-item-label">Check-out</div>
                      <div className="meta-item-value">
                        {hotel.check_out}
                      </div>
                    </div>
                  )}

                  {hotel.booking_reference && (
                    <div>
                      <div className="meta-item-label">Reference</div>
                      <div className="meta-item-value mono">
                        {hotel.booking_reference}
                      </div>
                    </div>
                  )}

                  {hotel.notes && (
                    <div>
                      <div className="meta-item-label">Notes</div>
                      <div className="meta-item-value">
                        {hotel.notes}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {/* ---------------- Expense limits ---------------- */}
      <SectionCard
        title="Expense limits"
        subtitle={
          canConfigureLimits
            ? "Configure the approved limits and the advance for this trip."
            : "Approved limits for this trip, configured by the travel desk."
        }
        actions={
          canConfigureLimits ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setLimitsForm({
                  max_approved_expenses:
                    config?.max_approved_expenses ?? "",
                  advance_amount: config?.advance_amount ?? "",
                  daily_allowance: config?.daily_allowance ?? "",
                  currency: config?.currency || "INR",
                });
                setShowLimitsForm(true);
              }}
              disabled={busy}
            >
              {config ? "Edit Limits" : "Configure Limits"}
            </Button>
          ) : undefined
        }
      >
        {config ? (
          <>
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
                <div className="kpi-label">Verified Expenses</div>
                <div className="kpi-value kpi-value--primary">
                  {formatMoney(verifiedTotal, config.currency)}
                </div>
              </div>

              <div className="kpi" style={{ boxShadow: "none" }}>
                <div className="kpi-label">Remaining Balance</div>
                <div
                  className={`kpi-value ${
                    remainingBalance != null &&
                    remainingBalance < 0
                      ? "kpi-value--danger"
                      : "kpi-value--success"
                  }`}
                >
                  {formatMoney(remainingBalance, config.currency)}
                </div>
              </div>
            </div>
          </>
        ) : (
          <p className="secondary mb-0">
            Expense limits have not been configured yet.
          </p>
        )}
      </SectionCard>

      {/* ---------------- Expenses ---------------- */}
      <SectionCard
        title="Expenses"
        subtitle="Expenses claimed for this trip."
      >
        {expenses.length === 0 ? (
          <EmptyState
            icon="🧾"
            title="No expenses submitted"
            description={
              canAddExpenses
                ? "Add your first expense using the form below."
                : "Expenses will appear here once the employee submits them."
            }
          />
        ) : (
          <>
            <Table
              columns={[
                { key: "date", label: "Date" },
                { key: "category", label: "Category" },
                { key: "amount", label: "Amount" },
                { key: "status", label: "Status" },
                ...(canVerifyExpenses
                  ? [
                      {
                        key: "actions",
                        label: "Actions",
                        align: "right",
                      },
                    ]
                  : []),
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
                        EXPENSE_STATUS_VARIANTS[expense.status] ||
                        "neutral"
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

                  {canVerifyExpenses && (
                    <td style={{ textAlign: "right" }}>
                      {expense.status === "SUBMITTED" && (
                        <div
                          className="btn-row"
                          style={{ justifyContent: "flex-end" }}
                        >
                          <Button
                            size="sm"
                            onClick={() =>
                              verifyExpense(expense.id, "VERIFIED")
                            }
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
                  )}
                </tr>
              ))}
            </Table>

            {config && (
              <p className="mt-1 mb-0 secondary">
                Verified total:{" "}
                <strong>
                  {formatMoney(verifiedTotal, displayCurrency)}
                </strong>
              </p>
            )}
          </>
        )}

        {canAddExpenses && (
          <>
            <hr className="divider" />

            <h3>Add expense</h3>

            <form onSubmit={submitExpense}>
              <div className="form-grid">
                <FormField
                  label="Category"
                  htmlFor="expense-category"
                  required
                >
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
                        {EXPENSE_CATEGORY_LABELS[category] ||
                          category}
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
                  label="Currency"
                  htmlFor="expense-currency"
                  required
                >
                  <select
                    id="expense-currency"
                    className="select"
                    value={expenseForm.currency}
                    onChange={(event) =>
                      setExpenseForm({
                        ...expenseForm,
                        currency: event.target.value,
                      })
                    }
                  >
                    {CURRENCIES.map((code) => (
                      <option key={code} value={code}>
                        {code}
                      </option>
                    ))}
                  </select>
                </FormField>

                <div className="form-field--full">
                  <FormField
                    label="Description (optional)"
                    htmlFor="expense-description"
                  >
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
          </>
        )}
      </SectionCard>

      {/* ---------------- Settlement ---------------- */}
      <SectionCard
        title="Settlement"
        subtitle="Final expense settlement for this trip."
      >
        {!settlement ? (
          <>
            <EmptyState
              icon="💰"
              title="Settlement not calculated yet"
              description={
                canCalculateSettlement
                  ? "The eligible expenses, allowances and advance are totaled into the settlement."
                  : "The settlement becomes available after expenses are verified and the workflow reaches settlement."
              }
            />

            {canCalculateSettlement && (
              <div className="btn-row">
                <Button
                  variant="secondary"
                  onClick={calculateSettlement}
                  disabled={busy}
                  loading={busy}
                >
                  Calculate Settlement
                </Button>
              </div>
            )}
          </>
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
                  settlement.status === "COMPLETED" ||
                  settlement.status === "APPROVED"
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

        {settlementLifecycle && (
          <div className="btn-row mt-2">
            {settlementLifecycle.canStartApproval && (
              <Button
                onClick={() => settlementAction("start-approval")}
                disabled={busy}
              >
                Send for Approval
              </Button>
            )}

            {settlementLifecycle.canApprove && (
              <Button
                onClick={() => settlementAction("approve")}
                disabled={busy}
              >
                Approve Settlement
              </Button>
            )}

            {settlementLifecycle.canProcess && (
              <Button
                onClick={() => setShowProcessPayment(true)}
                disabled={busy}
              >
                Process Payment
              </Button>
            )}

            {settlement.status === "PROCESSING" && (
              <span className="secondary">
                Payment processing…
              </span>
            )}

            {settlement.status === "COMPLETED" && (
              <span className="secondary">Settlement completed.</span>
            )}
          </div>
        )}
      </SectionCard>

      {/* Flight booking modal */}
      {showFlightForm && (
        <Modal
          title="Record Flight Booking"
          onClose={() => setShowFlightForm(false)}
        >
          <form onSubmit={submitFlight}>
            <div className="form-grid">
              <FormField
                label="Airline"
                htmlFor="flight-airline"
                required
              >
                <input
                  id="flight-airline"
                  className="input"
                  type="text"
                  required
                  placeholder="e.g. Air France"
                  value={flightForm.airline}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      airline: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Flight number"
                htmlFor="flight-number"
                required
              >
                <input
                  id="flight-number"
                  className="input"
                  type="text"
                  required
                  placeholder="e.g. AF109"
                  value={flightForm.flight_number}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      flight_number: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Departure date"
                htmlFor="flight-departure-date"
                required
              >
                <input
                  id="flight-departure-date"
                  className="input"
                  type="date"
                  required
                  value={flightForm.departure_date}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      departure_date: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Departure time"
                htmlFor="flight-departure-time"
                required
              >
                <input
                  id="flight-departure-time"
                  className="input"
                  type="time"
                  required
                  value={flightForm.departure_time}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      departure_time: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Arrival date"
                htmlFor="flight-arrival-date"
              >
                <input
                  id="flight-arrival-date"
                  className="input"
                  type="date"
                  value={flightForm.arrival_date}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      arrival_date: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Arrival time"
                htmlFor="flight-arrival-time"
              >
                <input
                  id="flight-arrival-time"
                  className="input"
                  type="time"
                  value={flightForm.arrival_time}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      arrival_time: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField label="From" htmlFor="flight-origin" required>
                <input
                  id="flight-origin"
                  className="input"
                  type="text"
                  required
                  placeholder="Departure city/airport"
                  value={flightForm.origin}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      origin: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField label="To" htmlFor="flight-destination" required>
                <input
                  id="flight-destination"
                  className="input"
                  type="text"
                  required
                  placeholder="Arrival city/airport"
                  value={flightForm.destination}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      destination: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Booking reference"
                htmlFor="flight-reference"
                required
              >
                <input
                  id="flight-reference"
                  className="input"
                  type="text"
                  required
                  placeholder="Airline PNR"
                  value={flightForm.booking_reference}
                  onChange={(event) =>
                    setFlightForm({
                      ...flightForm,
                      booking_reference: event.target.value,
                    })
                  }
                />
              </FormField>

              <div className="form-field--full">
                <FormField label="Notes" htmlFor="flight-notes">
                  <textarea
                    id="flight-notes"
                    className="textarea"
                    rows={2}
                    placeholder="Optional notes for the traveller…"
                    value={flightForm.notes}
                    onChange={(event) =>
                      setFlightForm({
                        ...flightForm,
                        notes: event.target.value,
                      })
                    }
                  />
                </FormField>
              </div>
            </div>

            <div className="btn-row mt-2">
              <Button type="submit" disabled={busy} loading={busy}>
                Save Flight Booking
              </Button>

              <Button
                variant="secondary"
                onClick={() => setShowFlightForm(false)}
                disabled={busy}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Hotel booking modal */}
      {showHotelForm && (
        <Modal
          title="Record Hotel Booking"
          onClose={() => setShowHotelForm(false)}
        >
          <form onSubmit={submitHotel}>
            <div className="form-grid">
              <FormField
                label="Hotel name"
                htmlFor="hotel-name"
                required
              >
                <input
                  id="hotel-name"
                  className="input"
                  type="text"
                  required
                  placeholder="e.g. Hotel Lumiere"
                  value={hotelForm.hotel_name}
                  onChange={(event) =>
                    setHotelForm({
                      ...hotelForm,
                      hotel_name: event.target.value,
                    })
                  }
                />
              </FormField>

              <div className="form-field--full">
                <FormField label="Address" htmlFor="hotel-address">
                  <textarea
                    id="hotel-address"
                    className="textarea"
                    rows={2}
                    placeholder="Hotel street address"
                    value={hotelForm.address}
                    onChange={(event) =>
                      setHotelForm({
                        ...hotelForm,
                        address: event.target.value,
                      })
                    }
                  />
                </FormField>
              </div>

              <FormField
                label="Check-in date"
                htmlFor="hotel-check-in"
                required
              >
                <input
                  id="hotel-check-in"
                  className="input"
                  type="date"
                  required
                  value={hotelForm.check_in}
                  onChange={(event) =>
                    setHotelForm({
                      ...hotelForm,
                      check_in: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Check-out date"
                htmlFor="hotel-check-out"
                required
              >
                <input
                  id="hotel-check-out"
                  className="input"
                  type="date"
                  required
                  value={hotelForm.check_out}
                  onChange={(event) =>
                    setHotelForm({
                      ...hotelForm,
                      check_out: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Booking reference"
                htmlFor="hotel-reference"
                required
              >
                <input
                  id="hotel-reference"
                  className="input"
                  type="text"
                  required
                  placeholder="Hotel confirmation code"
                  value={hotelForm.booking_reference}
                  onChange={(event) =>
                    setHotelForm({
                      ...hotelForm,
                      booking_reference: event.target.value,
                    })
                  }
                />
              </FormField>

              <div className="form-field--full">
                <FormField label="Notes" htmlFor="hotel-notes">
                  <textarea
                    id="hotel-notes"
                    className="textarea"
                    rows={2}
                    placeholder="Optional notes for the traveller…"
                    value={hotelForm.notes}
                    onChange={(event) =>
                      setHotelForm({
                        ...hotelForm,
                        notes: event.target.value,
                      })
                    }
                  />
                </FormField>
              </div>
            </div>

            <div className="btn-row mt-2">
              <Button type="submit" disabled={busy} loading={busy}>
                Save Hotel Booking
              </Button>

              <Button
                variant="secondary"
                onClick={() => setShowHotelForm(false)}
                disabled={busy}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Expense limits modal */}
      {showLimitsForm && (
        <Modal
          title="Configure Expense Limits"
          onClose={() => setShowLimitsForm(false)}
        >
          <form onSubmit={submitLimits}>
            <div className="form-grid">
              <FormField
                label="Maximum approved expenses"
                htmlFor="limits-max"
              >
                <input
                  id="limits-max"
                  className="input"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={limitsForm.max_approved_expenses}
                  onChange={(event) =>
                    setLimitsForm({
                      ...limitsForm,
                      max_approved_expenses: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Advance amount"
                htmlFor="limits-advance"
              >
                <input
                  id="limits-advance"
                  className="input"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={limitsForm.advance_amount}
                  onChange={(event) =>
                    setLimitsForm({
                      ...limitsForm,
                      advance_amount: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField
                label="Daily allowance"
                htmlFor="limits-daily"
              >
                <input
                  id="limits-daily"
                  className="input"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={limitsForm.daily_allowance}
                  onChange={(event) =>
                    setLimitsForm({
                      ...limitsForm,
                      daily_allowance: event.target.value,
                    })
                  }
                />
              </FormField>

              <FormField label="Currency" htmlFor="limits-currency" required>
                <select
                  id="limits-currency"
                  className="select"
                  value={limitsForm.currency}
                  onChange={(event) =>
                    setLimitsForm({
                      ...limitsForm,
                      currency: event.target.value,
                    })
                  }
                >
                  {CURRENCIES.map((code) => (
                    <option key={code} value={code}>
                      {code}
                    </option>
                  ))}
                </select>
              </FormField>
            </div>

            <div className="btn-row mt-2">
              <Button type="submit" disabled={busy} loading={busy}>
                Save Limits
              </Button>

              <Button
                variant="secondary"
                onClick={() => setShowLimitsForm(false)}
                disabled={busy}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Modal>
      )}

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
