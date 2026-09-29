import { useCallback, useEffect, useState } from "react";
import apiClient from "../api/client";

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

function Section({ title, children }) {
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
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </div>
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
      const data = err.response?.data;

      setActionError(
        typeof data === "string"
          ? data
          : data?.detail ||
            Object.values(data || {})[0]?.[0] ||
            "Action failed."
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

  const verifyExpense = (expenseId, decision) =>
    runAction(async () => {
      await apiClient.post(
        `travel-requests/${travelRequestId}/expenses/${expenseId}/verify/`,
        decision === "REJECTED"
          ? {
              status: "REJECTED",
              review_comments:
                window.prompt(
                  "Rejection comments (required):"
                ) || "",
            }
          : { status: decision }
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

  const money = (value, currency) =>
    value != null
      ? `${value} ${currency || ""}`.trim()
      : "-";

  return (
    <div>
      {loadError && (
        <p style={{ color: "#c62828" }}>{loadError}</p>
      )}

      {/* ---------------- Visa ---------------- */}
      {visa && (
        <Section title="Visa">
          <p>
            <strong>State:</strong> {visa.state}
          </p>

          {visa.country && (
            <p>
              <strong>Country:</strong> {visa.country}
            </p>
          )}

          {visa.applied_on && (
            <p>
              <strong>Applied on:</strong>{" "}
              {visa.applied_on}
            </p>
          )}

          {visa.remarks && (
            <p>
              <strong>Remarks:</strong> {visa.remarks}
            </p>
          )}

          {["NOT_APPLIED", "REJECTED"].includes(
            visa.state
          ) && (
            <button onClick={applyVisa} disabled={busy}>
              Apply for Visa
            </button>
          )}

          {["APPLIED", "UNDER_PROCESS"].includes(
            visa.state
          ) && (
            <>
              <button
                onClick={() => decideVisa("APPROVED")}
                disabled={busy}
              >
                Mark Approved
              </button>

              <button
                onClick={() => decideVisa("REJECTED")}
                disabled={busy}
                style={{ marginLeft: "8px" }}
              >
                Mark Rejected
              </button>

              <button
                onClick={() =>
                  decideVisa("UNDER_PROCESS")
                }
                disabled={busy}
                style={{ marginLeft: "8px" }}
              >
                Mark Under Process
              </button>
            </>
          )}
        </Section>
      )}

      {/* ---------------- Bookings ---------------- */}
      <Section title="Flight Bookings">
        {flights.length === 0 ? (
          <p>No flight bookings recorded.</p>
        ) : (
          flights.map((flight) => (
            <p key={flight.id}>
              {flight.airline || "Airline TBD"}{" "}
              {flight.flight_number} —{" "}
              {flight.booking_reference} ({flight.status})
            </p>
          ))
        )}

        <button onClick={addFlight} disabled={busy}>
          Record Flight Booking
        </button>
      </Section>

      <Section title="Hotel Bookings">
        {hotels.length === 0 ? (
          <p>No hotel bookings recorded.</p>
        ) : (
          hotels.map((hotel) => (
            <p key={hotel.id}>
              {hotel.hotel_name || "Hotel TBD"} —{" "}
              {hotel.booking_reference} ({hotel.status})
            </p>
          ))
        )}

        <button onClick={addHotel} disabled={busy}>
          Record Hotel Booking
        </button>
      </Section>

      {/* -------- Expense configuration -------- */}
      {config && (
        <Section title="Expense Configuration">
          <p>
            <strong>Max approved expenses:</strong>{" "}
            {money(
              config.max_approved_expenses,
              config.currency
            )}
          </p>

          <p>
            <strong>Advance given:</strong>{" "}
            {money(
              config.advance_amount,
              config.currency
            )}{" "}
            {config.advance_paid ? "(paid)" : "(not paid)"}
          </p>

          <p>
            <strong>Daily allowance:</strong>{" "}
            {money(config.daily_allowance, config.currency)}
          </p>
        </Section>
      )}

      {/* ---------------- Expenses ---------------- */}
      <Section title="Expenses">
        {expenses.length === 0 ? (
          <p>No expenses submitted.</p>
        ) : (
          <table style={{ width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Date</th>
                <th align="left">Category</th>
                <th align="left">Amount</th>
                <th align="left">Status</th>
                <th align="left">Actions</th>
              </tr>
            </thead>

            <tbody>
              {expenses.map((expense) => (
                <tr key={expense.id}>
                  <td>{expense.expense_date}</td>

                  <td>{expense.category}</td>

                  <td>
                    {money(
                      expense.amount,
                      expense.currency
                    )}
                  </td>

                  <td>{expense.status}</td>

                  <td>
                    {expense.status === "SUBMITTED" && (
                      <>
                        <button
                          onClick={() =>
                            verifyExpense(
                              expense.id,
                              "VERIFIED"
                            )
                          }
                          disabled={busy}
                        >
                          Verify
                        </button>

                        <button
                          style={{ marginLeft: "6px" }}
                          onClick={() =>
                            verifyExpense(
                              expense.id,
                              "REJECTED"
                            )
                          }
                          disabled={busy}
                        >
                          Reject
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <h4>Submit new expense</h4>

        <form onSubmit={submitExpense}>
          <select
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
                {category}
              </option>
            ))}
          </select>

          <input
            type="date"
            required
            value={expenseForm.expense_date}
            onChange={(event) =>
              setExpenseForm({
                ...expenseForm,
                expense_date: event.target.value,
              })
            }
            style={{ marginLeft: "8px" }}
          />

          <input
            type="number"
            step="0.01"
            min="0.01"
            required
            placeholder="Amount"
            value={expenseForm.amount}
            onChange={(event) =>
              setExpenseForm({
                ...expenseForm,
                amount: event.target.value,
              })
            }
            style={{ marginLeft: "8px", width: "110px" }}
          />

          <input
            type="text"
            placeholder="Currency (optional)"
            maxLength={3}
            value={expenseForm.currency}
            onChange={(event) =>
              setExpenseForm({
                ...expenseForm,
                currency: event.target.value.toUpperCase(),
              })
            }
            style={{ marginLeft: "8px", width: "90px" }}
          />

          <input
            type="text"
            placeholder="Description (optional)"
            value={expenseForm.description}
            onChange={(event) =>
              setExpenseForm({
                ...expenseForm,
                description: event.target.value,
              })
            }
            style={{ marginLeft: "8px", width: "180px" }}
          />

          <button
            type="submit"
            disabled={busy}
            style={{ marginLeft: "8px" }}
          >
            Add Expense
          </button>
        </form>
      </Section>

      {/* ---------------- Settlement ---------------- */}
      <Section title="Settlement">
        {!settlement ? (
          <p>Not calculated yet.</p>
        ) : (
          <>
            <p>
              <strong>Status:</strong>{" "}
              {settlement.status}
            </p>

            <p>
              <strong>Eligible expenses:</strong>{" "}
              {money(
                settlement.eligible_expenses_total,
                settlement.currency
              )}
            </p>

            <p>
              <strong>Rejected expenses:</strong>{" "}
              {money(
                settlement.rejected_expenses_total,
                settlement.currency
              )}
            </p>

            <p>
              <strong>Allowances:</strong>{" "}
              {money(
                settlement.allowances_total,
                settlement.currency
              )}
            </p>

            <p>
              <strong>Advance paid:</strong>{" "}
              {money(
                settlement.advance_paid,
                settlement.currency
              )}
            </p>

            <p>
              <strong>
                Net settlement:
              </strong>{" "}
              {money(
                settlement.net_settlement,
                settlement.currency
              )}{" "}
              {Number(settlement.net_settlement) < 0
                ? "(employee owes company)"
                : Number(settlement.net_settlement) > 0
                ? "(company owes employee)"
                : ""}
            </p>

            {settlement.status === "APPROVED" && (
              <div>
                <h4>Process payment</h4>

                <input
                  type="date"
                  value={settlementForm.payment_date}
                  onChange={(event) =>
                    setSettlementForm({
                      ...settlementForm,
                      payment_date: event.target.value,
                    })
                  }
                />

                <input
                  type="text"
                  placeholder="Payment reference"
                  value={
                    settlementForm.payment_reference
                  }
                  onChange={(event) =>
                    setSettlementForm({
                      ...settlementForm,
                      payment_reference:
                        event.target.value,
                    })
                  }
                  style={{ marginLeft: "8px" }}
                />

                <input
                  type="text"
                  placeholder="Payment method"
                  value={settlementForm.payment_method}
                  onChange={(event) =>
                    setSettlementForm({
                      ...settlementForm,
                      payment_method:
                        event.target.value,
                    })
                  }
                  style={{ marginLeft: "8px" }}
                />

                <button
                  onClick={() =>
                    settlementAction("start-processing")
                  }
                  disabled={busy}
                  style={{ marginLeft: "8px" }}
                >
                  Process Settlement
                </button>
              </div>
            )}
          </>
        )}

        <div style={{ marginTop: "12px" }}>
          <button
            onClick={calculateSettlement}
            disabled={busy}
          >
            Calculate Settlement
          </button>

          {settlement?.status === "PENDING" && (
            <button
              onClick={() =>
                settlementAction("start-approval")
              }
              disabled={busy}
              style={{ marginLeft: "8px" }}
            >
              Send for Approval
            </button>
          )}

          {settlement?.status === "IN_APPROVAL" && (
            <button
              onClick={() => settlementAction("approve")}
              disabled={busy}
              style={{ marginLeft: "8px" }}
            >
              Approve Settlement
            </button>
          )}

          {settlement?.status === "COMPLETED" && (
            <p>Settlement completed.</p>
          )}
        </div>
      </Section>

      {actionError && (
        <p style={{ color: "#c62828" }}>{actionError}</p>
      )}
    </div>
  );
}

export default TravelSections;
