import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

function ReviewerTravelRequests() {
  const navigate = useNavigate();

  const [travelRequests, setTravelRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTravelRequests();
  }, []);

  const fetchTravelRequests = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await apiClient.get(
        "travel-requests/"
      );

      setTravelRequests(response.data);
    } catch (err) {
      console.error("Failed to load travel requests:", err);

      if (err.response?.status === 401) {
        setError(
          "Your session has expired. Please login again."
        );
      } else if (err.response?.status === 403) {
        setError(
          "You do not have permission to view these travel requests."
        );
      } else {
        setError(
          "Failed to load travel requests."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (status) => {
    const statusLabels = {
      DRAFT: "Draft",
      SUBMITTED: "Submitted",
      DOCUMENT_PENDING: "Documents Pending",
      DOCUMENT_VERIFICATION:
        "Document Verification",
      APPROVED: "Approved",
      REJECTED: "Rejected",
      CANCELLED: "Cancelled",
    };

    return statusLabels[status] || status;
  };

  const getStatusColor = (status) => {
    if (status === "DOCUMENT_VERIFICATION") {
      return "green";
    }

    if (status === "DOCUMENT_PENDING") {
      return "orange";
    }

    if (status === "APPROVED") {
      return "green";
    }

    if (
      status === "REJECTED" ||
      status === "CANCELLED"
    ) {
      return "red";
    }

    return "gray";
  };

  if (loading) {
    return (
      <div style={{ padding: "30px" }}>
        <h1>Reviewer Travel Requests</h1>
        <p>Loading travel requests...</p>
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "30px",
      }}
    >
      {/* Header */}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "25px",
        }}
      >
        <div>
          <h1>Reviewer Travel Requests</h1>

          <p>
            Travel requests requiring document
            verification.
          </p>
        </div>

        <button
          onClick={() =>
            navigate("/dashboard")
          }
        >
          Back to Dashboard
        </button>
      </div>

      {/* Error */}

      {error && (
        <div
          style={{
            padding: "15px",
            marginBottom: "20px",
            border: "1px solid red",
            borderRadius: "6px",
            color: "red",
          }}
        >
          {error}
        </div>
      )}

      {/* Empty State */}

      {!error && travelRequests.length === 0 && (
        <div
          style={{
            padding: "30px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            textAlign: "center",
          }}
        >
          <h2>No Travel Requests</h2>

          <p>
            There are currently no travel requests
            requiring document review.
          </p>
        </div>
      )}

      {/* Travel Requests Table */}

      {!error && travelRequests.length > 0 && (
        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            overflowX: "auto",
          }}
        >
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Request Number
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Employee
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Destination
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Client
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Project
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Travel Type
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Start Date
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Status
                </th>

                <th
                  style={{
                    padding: "12px",
                    textAlign: "left",
                    borderBottom:
                      "1px solid #ddd",
                  }}
                >
                  Action
                </th>
              </tr>
            </thead>

            <tbody>
              {travelRequests.map(
                (travelRequest) => (
                  <tr key={travelRequest.id}>
                    {/* Request Number */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.request_number}
                    </td>

                    {/* Employee */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.employee_name ||
                        `Employee ID: ${travelRequest.employee}`}
                    </td>

                    {/* Destination */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.country_name ||
                        travelRequest.destination_country}

                      {travelRequest.destination_city && (
                        <>
                          <br />
                          {travelRequest.destination_city}
                        </>
                      )}
                    </td>

                    {/* Client */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.client}
                    </td>

                    {/* Project */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.project}
                    </td>

                    {/* Travel Type */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.travel_type}
                    </td>

                    {/* Start Date */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {travelRequest.start_date}
                    </td>

                    {/* Status */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      <span
                        style={{
                          color:
                            getStatusColor(
                              travelRequest.status
                            ),
                          fontWeight: "bold",
                        }}
                      >
                        {getStatusLabel(
                          travelRequest.status
                        )}
                      </span>
                    </td>

                    {/* Action */}

                    <td
                      style={{
                        padding: "12px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      <button
                        onClick={() =>
                          navigate(
                            `/reviewer/travel-requests/${travelRequest.id}`
                          )
                        }
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Refresh */}

      <div style={{ marginTop: "20px" }}>
        <button
          onClick={fetchTravelRequests}
        >
          Refresh
        </button>
      </div>
    </div>
  );
}

export default ReviewerTravelRequests;