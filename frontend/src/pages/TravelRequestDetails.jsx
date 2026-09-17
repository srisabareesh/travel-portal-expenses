import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../api/client";

function TravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [travelRequest, setTravelRequest] = useState(null);
  const [checklist, setChecklist] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTravelRequestDetails();
  }, [id]);

  // --------------------------------
  // Fetch Travel Request + Checklist
  // --------------------------------

  const fetchTravelRequestDetails = async () => {
    try {
      setLoading(true);
      setError("");

      const [requestResponse, checklistResponse] =
        await Promise.all([
          apiClient.get(`travel-requests/${id}/`),
          apiClient.get(`travel-requests/${id}/documents/`),
        ]);

      // Travel request
      setTravelRequest(requestResponse.data);

      // --------------------------------
      // Safely handle checklist response
      // --------------------------------

      const checklistData = checklistResponse.data;

      if (Array.isArray(checklistData)) {
        setChecklist(checklistData);
      } else if (Array.isArray(checklistData.results)) {
        setChecklist(checklistData.results);
      } else if (Array.isArray(checklistData.checklist)) {
        setChecklist(checklistData.checklist);
      } else {
        console.error(
          "Unexpected checklist API response:",
          checklistData
        );

        setChecklist([]);
      }
    } catch (err) {
      console.error(
        "Failed to load travel request details:",
        err
      );

      if (err.response?.status === 404) {
        setError("Travel request not found.");
      } else if (err.response?.status === 403) {
        setError(
          "You do not have permission to view this travel request."
        );
      } else if (err.response?.status === 401) {
        setError(
          "Your session has expired. Please login again."
        );
      } else {
        setError(
          "Failed to load travel request details."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------
  // Request Status
  // --------------------------------

  const getStatusLabel = (status) => {
    const statusLabels = {
      DRAFT: "Draft",
      SUBMITTED: "Submitted",
      DOCUMENT_PENDING: "Documents Pending",
      DOCUMENT_VERIFICATION: "Document Verification",
      APPROVED: "Approved",
      REJECTED: "Rejected",
      CANCELLED: "Cancelled",
    };

    return statusLabels[status] || status || "-";
  };

  // --------------------------------
  // Document Status
  // --------------------------------

  const getDocumentStatusLabel = (status) => {
    const statusLabels = {
      MISSING: "Missing",
      UPLOADED: "Uploaded",
      PENDING_REVIEW: "Pending Review",
      VERIFIED: "Verified",
      REJECTED: "Rejected",
      EXPIRED: "Expired",
      EXPIRING_SOON: "Expiring Soon",
    };

    return statusLabels[status] || status || "-";
  };

  const getDocumentStatusColor = (status) => {
    if (status === "VERIFIED") {
      return "green";
    }

    if (
      status === "REJECTED" ||
      status === "MISSING" ||
      status === "EXPIRED"
    ) {
      return "red";
    }

    if (
      status === "PENDING_REVIEW" ||
      status === "UPLOADED" ||
      status === "EXPIRING_SOON"
    ) {
      return "orange";
    }

    return "gray";
  };

  // --------------------------------
  // Loading
  // --------------------------------

  if (loading) {
    return (
      <div style={{ padding: "30px" }}>
        <h1>Travel Request Details</h1>

        <p>Loading travel request...</p>
      </div>
    );
  }

  // --------------------------------
  // Error
  // --------------------------------

  if (error) {
    return (
      <div style={{ padding: "30px" }}>
        <p style={{ color: "red" }}>{error}</p>

        <button
          onClick={() =>
            navigate("/travel-requests")
          }
        >
          Back to My Travel Requests
        </button>
      </div>
    );
  }

  // --------------------------------
  // No Travel Request
  // --------------------------------

  if (!travelRequest) {
    return null;
  }

  // --------------------------------
  // Document Statistics
  // --------------------------------

  const totalDocuments = checklist.length;

  const verifiedDocuments = checklist.filter(
    (document) =>
      document.status === "VERIFIED"
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

  // --------------------------------
  // Upload Action
  // --------------------------------

  const needsDocumentAction = checklist.some(
    (document) =>
      document.status === "MISSING" ||
      document.status === "REJECTED"
  );

  // --------------------------------
  // Page
  // --------------------------------

  return (
    <div
      style={{
        maxWidth: "1000px",
        margin: "0 auto",
        padding: "30px",
      }}
    >
      {/* -------------------------------- */}
      {/* Header */}
      {/* -------------------------------- */}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "25px",
        }}
      >
        <div>
          <h1>Travel Request Details</h1>

          <p>
            <strong>Request Number:</strong>{" "}
            {travelRequest.request_number}
          </p>
        </div>

        <button
          onClick={() =>
            navigate("/travel-requests")
          }
        >
          Back
        </button>
      </div>

      {/* -------------------------------- */}
      {/* Travel Information */}
      {/* -------------------------------- */}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "25px",
        }}
      >
        <h2>Travel Information</h2>

        <p>
          <strong>Destination Country:</strong>{" "}
          {travelRequest.country_name ||
            travelRequest.destination_country ||
            "-"}
        </p>

        <p>
          <strong>Destination City:</strong>{" "}
          {travelRequest.destination_city || "-"}
        </p>

        <p>
          <strong>Client:</strong>{" "}
          {travelRequest.client || "-"}
        </p>

        <p>
          <strong>Project:</strong>{" "}
          {travelRequest.project || "-"}
        </p>

        <p>
          <strong>Travel Type:</strong>{" "}
          {travelRequest.travel_type || "-"}
        </p>

        <p>
          <strong>Start Date:</strong>{" "}
          {travelRequest.start_date || "-"}
        </p>

        <p>
          <strong>End Date:</strong>{" "}
          {travelRequest.end_date || "-"}
        </p>

        <p>
          <strong>Purpose:</strong>{" "}
          {travelRequest.purpose || "-"}
        </p>

        <p>
          <strong>Request Status:</strong>{" "}
          <span
            style={{
              fontWeight: "bold",
            }}
          >
            {getStatusLabel(
              travelRequest.status
            )}
          </span>
        </p>
      </div>

      {/* -------------------------------- */}
      {/* Document Progress */}
      {/* -------------------------------- */}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "25px",
        }}
      >
        <h2>Document Progress</h2>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: "10px",
          }}
        >
          <span>
            <strong>
              {verifiedDocuments}
            </strong>{" "}
            of{" "}
            <strong>
              {totalDocuments}
            </strong>{" "}
            documents verified
          </span>

          <strong>
            {completionPercentage}%
          </strong>
        </div>

        {/* Progress Bar */}

        <div
          style={{
            width: "100%",
            height: "20px",
            backgroundColor: "#e5e5e5",
            borderRadius: "10px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${completionPercentage}%`,
              height: "100%",
              backgroundColor: "green",
              transition:
                "width 0.3s ease",
            }}
          />
        </div>

        {/* Statistics */}

        <div
          style={{
            display: "flex",
            gap: "30px",
            marginTop: "20px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <strong>Total</strong>
            <br />
            {totalDocuments}
          </div>

          <div>
            <strong>Verified</strong>
            <br />
            {verifiedDocuments}
          </div>

          <div>
            <strong>Pending</strong>
            <br />
            {pendingDocuments}
          </div>

          <div>
            <strong>Missing / Rejected</strong>
            <br />
            {missingDocuments}
          </div>
        </div>
      </div>

      {/* -------------------------------- */}
      {/* Upload Required Document */}
      {/* -------------------------------- */}

      {needsDocumentAction && (
        <div
          style={{
            marginBottom: "25px",
          }}
        >
          <button
            onClick={() =>
              navigate(
                `/travel-requests/${id}/documents/upload`
              )
            }
          >
            Upload Required Document
          </button>
        </div>
      )}

      {/* -------------------------------- */}
      {/* Document Checklist */}
      {/* -------------------------------- */}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "20px",
        }}
      >
        <h2>Document Checklist</h2>

        {checklist.length === 0 ? (
          <p>
            No documents are required for this
            travel request.
          </p>
        ) : (
          <div
            style={{
              overflowX: "auto",
              marginTop: "15px",
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
                      textAlign: "left",
                      padding: "10px",
                      borderBottom:
                        "1px solid #ddd",
                    }}
                  >
                    Document
                  </th>

                  <th
                    style={{
                      textAlign: "left",
                      padding: "10px",
                      borderBottom:
                        "1px solid #ddd",
                    }}
                  >
                    Mandatory
                  </th>

                  <th
                    style={{
                      textAlign: "left",
                      padding: "10px",
                      borderBottom:
                        "1px solid #ddd",
                    }}
                  >
                    Status
                  </th>

                  <th
                    style={{
                      textAlign: "left",
                      padding: "10px",
                      borderBottom:
                        "1px solid #ddd",
                    }}
                  >
                    Action
                  </th>
                </tr>
              </thead>

              <tbody>
                {checklist.map((document) => (
                  <tr
                    key={
                      document.document_type_id
                    }
                  >
                    {/* Document */}

                    <td
                      style={{
                        padding: "10px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      <strong>
                        {document.document_type ||
                          "-"}
                      </strong>
                    </td>

                    {/* Mandatory */}

                    <td
                      style={{
                        padding: "10px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {document.mandatory
                        ? "Yes"
                        : "No"}
                    </td>

                    {/* Status */}

                    <td
                      style={{
                        padding: "10px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      <span
                        style={{
                          color:
                            getDocumentStatusColor(
                              document.status
                            ),
                          fontWeight: "bold",
                        }}
                      >
                        {getDocumentStatusLabel(
                          document.status
                        )}
                      </span>
                    </td>

                    {/* Action */}

                    <td
                      style={{
                        padding: "10px",
                        borderBottom:
                          "1px solid #eee",
                      }}
                    >
                      {(document.status ===
                        "MISSING" ||
                        document.status ===
                          "REJECTED") && (
                        <button
                          onClick={() =>
                            navigate(
                              `/travel-requests/${id}/documents/upload`
                            )
                          }
                        >
                          Upload
                        </button>
                      )}

                      {document.status ===
                        "PENDING_REVIEW" && (
                        <span>
                          Waiting for review
                        </span>
                      )}

                      {document.status ===
                        "UPLOADED" && (
                        <span>
                          Uploaded - Waiting
                          for review
                        </span>
                      )}

                      {document.status ===
                        "VERIFIED" && (
                        <span
                          style={{
                            color: "green",
                            fontWeight: "bold",
                          }}
                        >
                          ✓ Verified
                        </span>
                      )}

                      {document.status ===
                        "EXPIRED" && (
                        <button
                          onClick={() =>
                            navigate(
                              `/travel-requests/${id}/documents/upload`
                            )
                          }
                        >
                          Upload New Document
                        </button>
                      )}

                      {document.status ===
                        "EXPIRING_SOON" && (
                        <span>
                          Expiring Soon
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* -------------------------------- */}
      {/* Refresh */}
      {/* -------------------------------- */}

      <div
        style={{
          marginTop: "20px",
        }}
      >
        <button
          onClick={fetchTravelRequestDetails}
        >
          Refresh
        </button>
      </div>
    </div>
  );
}

export default TravelRequestDetails;