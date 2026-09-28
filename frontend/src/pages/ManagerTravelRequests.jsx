import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import apiClient from "../api/client";


function ManagerTravelRequests() {
  const navigate = useNavigate();

  const [travelRequests, setTravelRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");


  const loadTravelRequests = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await apiClient.get(
        "travel-requests/"
      );

      const data = response.data;

      if (Array.isArray(data)) {
        setTravelRequests(data);
      } else if (Array.isArray(data.results)) {
        setTravelRequests(data.results);
      } else {
        setTravelRequests([]);
      }
    } catch (err) {
      console.error(
        "Failed to load travel requests:",
        err
      );

      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(
          "Failed to load travel requests."
        );
      }
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadTravelRequests();
  }, []);


  const getStatusLabel = (status) => {
    switch (status) {
      case "DRAFT":
        return "Draft";

      case "SUBMITTED":
        return "Submitted";

      case "DOCUMENT_PENDING":
        return "Document Pending";

      case "DOCUMENT_VERIFICATION":
        return "Document Verification";

      case "APPROVED":
        return "Approved";

      case "REJECTED":
        return "Rejected";

      case "CANCELLED":
        return "Cancelled";

      default:
        return status || "-";
    }
  };


  const getStatusStyle = (status) => {
    switch (status) {
      case "DRAFT":
        return {
          backgroundColor: "#f2f2f2",
          color: "#555",
        };

      case "SUBMITTED":
        return {
          backgroundColor: "#e8f1ff",
          color: "#1d5fa7",
        };

      case "DOCUMENT_PENDING":
        return {
          backgroundColor: "#fff4d6",
          color: "#8a6500",
        };

      case "DOCUMENT_VERIFICATION":
        return {
          backgroundColor: "#e8f5e9",
          color: "#2e7d32",
        };

      case "APPROVED":
        return {
          backgroundColor: "#e8f5e9",
          color: "#2e7d32",
        };

      case "REJECTED":
        return {
          backgroundColor: "#ffebee",
          color: "#c62828",
        };

      case "CANCELLED":
        return {
          backgroundColor: "#eeeeee",
          color: "#616161",
        };

      default:
        return {
          backgroundColor: "#f5f5f5",
          color: "#555",
        };
    }
  };


  if (loading) {
    return (
      <div
        style={{
          maxWidth: "1200px",
          margin: "40px auto",
          padding: "20px",
        }}
      >
        <h1>Manager Travel Requests</h1>

        <p>
          Loading travel requests...
        </p>
      </div>
    );
  }


  return (
    <div
      style={{
        maxWidth: "1200px",
        margin: "40px auto",
        padding: "20px",
      }}
    >

      <div
        style={{
          backgroundColor: "#ffffff",
          border: "1px solid #ddd",
          borderRadius: "10px",
          padding: "30px",
        }}
      >

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "25px",
            gap: "15px",
            flexWrap: "wrap",
          }}
        >

          <div>
            <h1
              style={{
                marginTop: 0,
                marginBottom: "8px",
              }}
            >
              Manager Travel Requests
            </h1>

            <p
              style={{
                margin: 0,
                color: "#666",
              }}
            >
              View your travel requests and
              requests submitted by your team.
            </p>
          </div>


          <button
            onClick={() =>
              navigate("/manager")
            }
          >
            Back to Dashboard
          </button>

        </div>


        {error && (
          <div
            style={{
              backgroundColor: "#ffebee",
              border: "1px solid #ef9a9a",
              borderRadius: "6px",
              padding: "12px",
              marginBottom: "20px",
              color: "#c62828",
            }}
          >
            {error}
          </div>
        )}


        {travelRequests.length === 0 ? (

          <div
            style={{
              padding: "30px",
              textAlign: "center",
              border: "1px solid #ddd",
              borderRadius: "8px",
              color: "#666",
            }}
          >
            No travel requests found.
          </div>

        ) : (

          <div
            style={{
              overflowX: "auto",
            }}
          >

            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: "900px",
              }}
            >

              <thead>

                <tr
                  style={{
                    backgroundColor: "#f5f5f5",
                  }}
                >

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    Request Number
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    Employee
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    Destination
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    Travel Type
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    Start Date
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    End Date
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "left",
                    }}
                  >
                    Status
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                    }}
                  >
                    Action
                  </th>

                </tr>

              </thead>


              <tbody>

                {travelRequests.map(
                  (travelRequest) => (

                    <tr
                      key={travelRequest.id}
                    >

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                          fontWeight: "600",
                        }}
                      >
                        {
                          travelRequest.request_number
                        }
                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        {
                          travelRequest.employee_name ||
                          travelRequest.employee ||
                          "-"
                        }
                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        <div>
                          {
                            travelRequest.country_name ||
                            travelRequest.destination_country ||
                            "-"
                          }
                        </div>

                        {travelRequest.destination_city && (
                          <div
                            style={{
                              fontSize: "13px",
                              color: "#666",
                              marginTop: "3px",
                            }}
                          >
                            {
                              travelRequest.destination_city
                            }
                          </div>
                        )}
                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        {
                          travelRequest.travel_type ||
                          "-"
                        }
                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        {
                          travelRequest.start_date ||
                          "-"
                        }
                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        {
                          travelRequest.end_date ||
                          "-"
                        }
                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >

                        <span
                          style={{
                            ...getStatusStyle(
                              travelRequest.status
                            ),
                            display: "inline-block",
                            padding:
                              "5px 10px",
                            borderRadius: "12px",
                            fontSize: "13px",
                            fontWeight: "600",
                          }}
                        >
                          {
                            getStatusLabel(
                              travelRequest.status
                            )
                          }
                        </span>

                      </td>


                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                          textAlign: "center",
                        }}
                      >

                        <button
                          onClick={() =>
                            navigate(
                              `/manager/travel-requests/${travelRequest.id}`
                            )
                          }
                        >
                          View Details
                        </button>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </div>

    </div>
  );
}


export default ManagerTravelRequests;