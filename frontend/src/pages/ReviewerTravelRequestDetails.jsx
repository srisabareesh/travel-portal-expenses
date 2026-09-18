import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../api/client";

function ReviewerTravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [travelRequest, setTravelRequest] = useState(null);
  const [documents, setDocuments] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedDocument, setSelectedDocument] = useState(null);
  const [reviewComments, setReviewComments] = useState("");
  const [processing, setProcessing] = useState(false);

  const [verificationHistory, setVerificationHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // --------------------------------------------------
  // Fetch Travel Request
  // --------------------------------------------------

  const fetchTravelRequest = async () => {
    try {
      const response = await apiClient.get(
        `travel-requests/${id}/`
      );

      setTravelRequest(response.data);
    } catch (error) {
      console.error(error);

      if (error.response?.status === 403) {
        setError(
          "You do not have permission to access this travel request."
        );
      } else if (error.response?.status === 404) {
        setError("Travel request not found.");
      } else {
        setError(
          "Unable to load travel request."
        );
      }
    }
  };

  // --------------------------------------------------
  // Fetch Documents
  // --------------------------------------------------

  const fetchDocuments = async () => {
    try {
      const response = await apiClient.get(
        `travel-requests/${id}/documents/`
      );

      // Backend returns:
      // {
      //   checklist: [...],
      //   all_mandatory_verified: true/false
      // }
      setDocuments(response.data.checklist);
    } catch (error) {
      console.error(error);

      if (error.response?.status === 403) {
        setError(
          "You do not have permission to view these documents."
        );
      } else {
        setError(
          "Unable to load travel documents."
        );
      }
    }
  };

  // --------------------------------------------------
  // Fetch Verification History
  // --------------------------------------------------

  const fetchVerificationHistory = async (
    documentId
  ) => {
    try {
      setHistoryLoading(true);

      const response = await apiClient.get(
        `documents/${documentId}/verification-history/`
      );

      setVerificationHistory(response.data);
    } catch (error) {
      console.error(error);

      setVerificationHistory([]);

      if (error.response?.status === 403) {
        setError(
          "You do not have permission to view verification history."
        );
      } else {
        setError(
          "Unable to load verification history."
        );
      }
    } finally {
      setHistoryLoading(false);
    }
  };

  // --------------------------------------------------
  // Fetch All Data
  // --------------------------------------------------

  const fetchData = async () => {
    setLoading(true);
    setError("");

    await Promise.all([
      fetchTravelRequest(),
      fetchDocuments(),
    ]);

    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  // --------------------------------------------------
  // Open Review
  // --------------------------------------------------

  const openReview = async (document) => {
    setSelectedDocument(document);
    setReviewComments("");
    setVerificationHistory([]);
    setError("");

    await fetchVerificationHistory(
      document.document_id
    );
  };

  // --------------------------------------------------
  // Close Review
  // --------------------------------------------------

  const closeReview = () => {
    setSelectedDocument(null);
    setReviewComments("");
    setVerificationHistory([]);
    setError("");
  };

  // --------------------------------------------------
  // Approve Document
  // --------------------------------------------------

  const handleApprove = async () => {
    if (!selectedDocument) {
      return;
    }

    setProcessing(true);
    setError("");

    try {
      await apiClient.post(
        `documents/${selectedDocument.document_id}/verify/`,
        {
          status: "APPROVED",
          comments:
            reviewComments.trim() ||
            "Document verified successfully.",
        }
      );

      alert(
        "Document approved successfully."
      );

      closeReview();

      await fetchData();
    } catch (error) {
      console.error(error);

      if (error.response?.data?.detail) {
        setError(
          error.response.data.detail
        );
      } else {
        setError(
          "Unable to approve the document."
        );
      }
    } finally {
      setProcessing(false);
    }
  };

  // --------------------------------------------------
  // Reject Document
  // --------------------------------------------------

  const handleReject = async () => {
    if (!selectedDocument) {
      return;
    }

    if (!reviewComments.trim()) {
      alert(
        "Comments are required when rejecting a document."
      );
      return;
    }

    setProcessing(true);
    setError("");

    try {
      await apiClient.post(
        `documents/${selectedDocument.document_id}/verify/`,
        {
          status: "REJECTED",
          comments: reviewComments.trim(),
        }
      );

      alert(
        "Document rejected successfully."
      );

      closeReview();

      await fetchData();
    } catch (error) {
      console.error(error);

      if (error.response?.data?.detail) {
        setError(
          error.response.data.detail
        );
      } else {
        setError(
          "Unable to reject the document."
        );
      }
    } finally {
      setProcessing(false);
    }
  };

  // --------------------------------------------------
// File URL Helper
// --------------------------------------------------

const getFileUrl = (file) => {
  if (!file) {
    return null;
  }

  if (
    file.startsWith("http://") ||
    file.startsWith("https://")
  ) {
    return file;
  }

  const normalizedFile = file.startsWith("/")
    ? file
    : `/${file}`;

  return `http://127.0.0.1:8000${normalizedFile}`;
};

  // --------------------------------------------------
  // Status Helpers
  // --------------------------------------------------

  const getStatusLabel = (status) => {
    switch (status) {
      case "MISSING":
        return "Missing";

      case "UPLOADED":
        return "Uploaded";

      case "PENDING_REVIEW":
        return "Pending Review";

      case "VERIFIED":
        return "Verified";

      case "REJECTED":
        return "Rejected";

      case "EXPIRED":
        return "Expired";

      case "EXPIRING_SOON":
        return "Expiring Soon";

      default:
        return status || "-";
    }
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case "VERIFIED":
        return {
          backgroundColor: "#d4edda",
          color: "#155724",
        };

      case "REJECTED":
        return {
          backgroundColor: "#f8d7da",
          color: "#721c24",
        };

      case "PENDING_REVIEW":
      case "UPLOADED":
        return {
          backgroundColor: "#fff3cd",
          color: "#856404",
        };

      case "MISSING":
        return {
          backgroundColor: "#f8d7da",
          color: "#721c24",
        };

      case "EXPIRING_SOON":
        return {
          backgroundColor: "#fff3cd",
          color: "#856404",
        };

      case "EXPIRED":
        return {
          backgroundColor: "#f8d7da",
          color: "#721c24",
        };

      default:
        return {
          backgroundColor: "#e2e3e5",
          color: "#383d41",
        };
    }
  };

  // --------------------------------------------------
  // Loading
  // --------------------------------------------------

  if (loading) {
    return (
      <div
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
          padding: "30px",
        }}
      >
        <p>Loading travel request...</p>
      </div>
    );
  }

  // --------------------------------------------------
  // Error
  // --------------------------------------------------

  if (error && !travelRequest) {
    return (
      <div
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
          padding: "30px",
        }}
      >
        <div
          style={{
            backgroundColor: "#f8d7da",
            color: "#721c24",
            padding: "12px 16px",
            borderRadius: "6px",
            marginBottom: "20px",
          }}
        >
          {error}
        </div>

        <button
          onClick={() =>
            navigate(
              "/reviewer/travel-requests"
            )
          }
          style={{
            padding: "9px 16px",
            border: "none",
            borderRadius: "5px",
            cursor: "pointer",
          }}
        >
          Back to Reviewer Requests
        </button>
      </div>
    );
  }

  if (!travelRequest) {
    return (
      <div
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
          padding: "30px",
        }}
      >
        <p>Travel request not found.</p>
      </div>
    );
  }

  // --------------------------------------------------
  // Document Counts
  // --------------------------------------------------

  const totalDocuments = documents.length;

  const pendingDocuments = documents.filter(
    (document) =>
      document.status === "UPLOADED" ||
      document.status === "PENDING_REVIEW"
  ).length;

  const verifiedDocuments = documents.filter(
    (document) =>
      document.status === "VERIFIED"
  ).length;

  const rejectedDocuments = documents.filter(
    (document) =>
      document.status === "REJECTED"
  ).length;

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div
      style={{
        maxWidth: "1100px",
        margin: "0 auto",
        padding: "30px",
        fontFamily:
          "Arial, Helvetica, sans-serif",
      }}
    >

      {/* ==================================================
          PAGE HEADER
          ================================================== */}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "25px",
        }}
      >
        <div>
          <h1
            style={{
              margin: "0 0 8px 0",
              fontSize: "28px",
            }}
          >
            Travel Request Details
          </h1>

          <p
            style={{
              margin: 0,
              color: "#666",
            }}
          >
            Review employee travel documents
          </p>
        </div>

        <span
          style={{
            ...getStatusStyle(
              travelRequest.status
            ),
            padding: "8px 14px",
            borderRadius: "20px",
            fontSize: "13px",
            fontWeight: "600",
          }}
        >
          {getStatusLabel(
            travelRequest.status
          )}
        </span>
      </div>

      {/* ==================================================
          ERROR MESSAGE
          ================================================== */}

      {error && (
        <div
          style={{
            backgroundColor: "#f8d7da",
            color: "#721c24",
            padding: "12px 16px",
            borderRadius: "6px",
            marginBottom: "20px",
          }}
        >
          {error}
        </div>
      )}

      {/* ==================================================
          TRAVEL REQUEST INFORMATION
          ================================================== */}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "25px",
          marginBottom: "25px",
          backgroundColor: "#fff",
        }}
      >
        <h2
          style={{
            marginTop: 0,
            marginBottom: "20px",
            fontSize: "21px",
          }}
        >
          Travel Request Information
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(250px, 1fr))",
            gap: "18px",
          }}
        >

          <div>
            <strong>
              Request Number
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.request_number ||
                "-"}
            </p>
          </div>

          <div>
            <strong>
              Employee
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.employee_name ||
                travelRequest.employee ||
                "-"}
            </p>
          </div>

          <div>
            <strong>
              Destination
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.destination_city ||
                "-"}
              {travelRequest.destination_country_name
                ? `, ${travelRequest.destination_country_name}`
                : ""}
            </p>
          </div>

          <div>
            <strong>
              Travel Type
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.travel_type ||
                "-"}
            </p>
          </div>

          <div>
            <strong>
              Start Date
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.start_date ||
                "-"}
            </p>
          </div>

          <div>
            <strong>
              End Date
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.end_date ||
                "-"}
            </p>
          </div>

          <div>
            <strong>
              Client
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.client || "-"}
            </p>
          </div>

          <div>
            <strong>
              Project
            </strong>

            <p
              style={{
                margin: "5px 0 0",
              }}
            >
              {travelRequest.project || "-"}
            </p>
          </div>

        </div>

        <div
          style={{
            marginTop: "20px",
          }}
        >
          <strong>
            Purpose
          </strong>

          <p
            style={{
              margin: "5px 0 0",
              lineHeight: "1.5",
            }}
          >
            {travelRequest.purpose || "-"}
          </p>
        </div>
      </div>

      {/* ==================================================
          DOCUMENT SUMMARY
          ================================================== */}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "25px",
          marginBottom: "25px",
          backgroundColor: "#fff",
        }}
      >
        <h2
          style={{
            marginTop: 0,
            marginBottom: "20px",
            fontSize: "21px",
          }}
        >
          Document Summary
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "15px",
          }}
        >

          <div
            style={{
              border: "1px solid #ddd",
              borderRadius: "7px",
              padding: "18px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "28px",
                fontWeight: "bold",
              }}
            >
              {totalDocuments}
            </div>

            <div
              style={{
                color: "#666",
                marginTop: "5px",
              }}
            >
              Total Documents
            </div>
          </div>

          <div
            style={{
              border: "1px solid #ddd",
              borderRadius: "7px",
              padding: "18px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "28px",
                fontWeight: "bold",
              }}
            >
              {pendingDocuments}
            </div>

            <div
              style={{
                color: "#856404",
                marginTop: "5px",
              }}
            >
              Pending Review
            </div>
          </div>

          <div
            style={{
              border: "1px solid #ddd",
              borderRadius: "7px",
              padding: "18px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "28px",
                fontWeight: "bold",
              }}
            >
              {verifiedDocuments}
            </div>

            <div
              style={{
                color: "#155724",
                marginTop: "5px",
              }}
            >
              Verified
            </div>
          </div>

          <div
            style={{
              border: "1px solid #ddd",
              borderRadius: "7px",
              padding: "18px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "28px",
                fontWeight: "bold",
              }}
            >
              {rejectedDocuments}
            </div>

            <div
              style={{
                color: "#721c24",
                marginTop: "5px",
              }}
            >
              Rejected
            </div>
          </div>

        </div>
      </div>

      {/* ==================================================
          EMPLOYEE DOCUMENTS
          ================================================== */}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "25px",
          marginBottom: "25px",
          backgroundColor: "#fff",
        }}
      >
        <h2
          style={{
            marginTop: 0,
            marginBottom: "20px",
            fontSize: "21px",
          }}
        >
          Employee Documents
        </h2>

        {documents.length === 0 ? (
          <p
            style={{
              color: "#666",
            }}
          >
            No documents found.
          </p>
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
                fontSize: "14px",
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
                    Document Type
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                    }}
                  >
                    Mandatory
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                    }}
                  >
                    Status
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                    }}
                  >
                    Issue Date
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                    }}
                  >
                    Expiry Date
                  </th>

                  <th
                    style={{
                      padding: "12px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody>
                {documents.map(
                  (document) => (
                    <tr
                      key={
                        document.document_id
                      }
                    >

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                          fontWeight: "500",
                        }}
                      >
                        {document.document_type ||
                          "-"}
                      </td>

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                          textAlign: "center",
                        }}
                      >
                        {document.mandatory
                          ? "Yes"
                          : "No"}
                      </td>

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                          textAlign: "center",
                        }}
                      >
                        <span
                          style={{
                            ...getStatusStyle(
                              document.status
                            ),
                            display:
                              "inline-block",
                            padding:
                              "5px 10px",
                            borderRadius:
                              "12px",
                            fontSize:
                              "12px",
                            fontWeight:
                              "600",
                          }}
                        >
                          {getStatusLabel(
                            document.status
                          )}
                        </span>
                      </td>

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        {document.issue_date ||
                          "-"}
                      </td>

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                        }}
                      >
                        {document.expiry_date ||
                          "-"}
                      </td>

                      <td
                        style={{
                          padding: "12px",
                          border: "1px solid #ddd",
                          textAlign: "center",
                        }}
                      >

                        {document.file && (
                          <a
                            href={getFileUrl(document.file)}
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              marginRight: "10px",
                              color: "#007bff",
                              textDecoration: "none",
                            }}
                          >
                            View Document
                          </a>
                        )}

                        {(
                          document.status ===
                            "UPLOADED" ||
                          document.status ===
                            "PENDING_REVIEW"
                        ) && (
                          <button
                            type="button"
                            onClick={() =>
                              openReview(
                                document
                              )
                            }
                            style={{
                              padding:
                                "6px 12px",
                              border: "none",
                              borderRadius:
                                "5px",
                              cursor:
                                "pointer",
                            }}
                          >
                            Review
                          </button>
                        )}

                        {document.status ===
                          "REJECTED" && (
                          <button
                            type="button"
                            onClick={() =>
                              openReview(
                                document
                              )
                            }
                            style={{
                              padding:
                                "6px 12px",
                              border: "1px solid #dc3545",
                              borderRadius:
                                "5px",
                              cursor:
                                "pointer",
                            }}
                          >
                            View Review
                          </button>
                        )}

                        {document.status ===
                          "VERIFIED" && (
                          <span
                            style={{
                              color:
                                "#155724",
                              fontWeight:
                                "600",
                            }}
                          >
                            ✓ Verified
                          </span>
                        )}

                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ==================================================
          DOCUMENT REVIEW PANEL
          ================================================== */}

      {selectedDocument && (
        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "25px",
            marginBottom: "25px",
            backgroundColor: "#fff",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "20px",
            }}
          >
            <h2
              style={{
                margin: 0,
                fontSize: "21px",
              }}
            >
              Document Review
            </h2>

            <button
              type="button"
              onClick={closeReview}
              disabled={processing}
              style={{
                padding: "6px 12px",
                border: "1px solid #ccc",
                borderRadius: "5px",
                backgroundColor: "#fff",
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>

          {/* Document Details */}

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "18px",
              marginBottom: "20px",
            }}
          >
            <div>
              <strong>
                Document Type
              </strong>

              <p
                style={{
                  margin: "5px 0",
                }}
              >
                {selectedDocument.document_type ||
                  "-"}
              </p>
            </div>

            <div>
              <strong>
                Status
              </strong>

              <p
                style={{
                  margin: "5px 0",
                }}
              >
                <span
                  style={{
                    ...getStatusStyle(
                      selectedDocument.status
                    ),
                    display:
                      "inline-block",
                    padding:
                      "5px 10px",
                    borderRadius:
                      "12px",
                    fontSize:
                      "12px",
                    fontWeight:
                      "600",
                  }}
                >
                  {getStatusLabel(
                    selectedDocument.status
                  )}
                </span>
              </p>
            </div>
          </div>

          {selectedDocument.file && (
            <div
              style={{
                marginBottom: "20px",
              }}
            >
              <a
                href={getFileUrl(selectedDocument.file)}
                target="_blank"
                rel="noreferrer"
                style={{
                  display:
                    "inline-block",
                  padding:
                    "9px 15px",
                  border:
                    "1px solid #007bff",
                  borderRadius:
                    "5px",
                  textDecoration:
                    "none",
                  color: "#007bff",
                }}
              >
                Open Document
              </a>
            </div>
          )}

          {/* Review Comments */}

          <div
            style={{
              marginBottom: "20px",
            }}
          >
            <label
              htmlFor="review-comments"
              style={{
                display:
                  "block",
                fontWeight:
                  "600",
                marginBottom:
                  "8px",
              }}
            >
              Review Comments
            </label>

            <textarea
              id="review-comments"
              rows="5"
              value={
                reviewComments
              }
              onChange={(event) =>
                setReviewComments(
                  event.target.value
                )
              }
              placeholder="Enter review comments..."
              disabled={processing}
              style={{
                width: "100%",
                maxWidth: "700px",
                padding: "10px",
                border:
                  "1px solid #ccc",
                borderRadius:
                  "5px",
                resize:
                  "vertical",
                boxSizing:
                  "border-box",
              }}
            />

            <p
              style={{
                fontSize: "12px",
                color: "#666",
                marginTop: "5px",
              }}
            >
              Comments are required when
              rejecting a document.
            </p>
          </div>

          {/* Review Buttons */}

          {(
            selectedDocument.status ===
              "UPLOADED" ||
            selectedDocument.status ===
              "PENDING_REVIEW"
          ) && (
            <div
              style={{
                marginBottom: "25px",
              }}
            >
              <button
                type="button"
                onClick={
                  handleApprove
                }
                disabled={
                  processing
                }
                style={{
                  padding:
                    "9px 18px",
                  border: "none",
                  borderRadius:
                    "5px",
                  cursor:
                    processing
                      ? "not-allowed"
                      : "pointer",
                  marginRight:
                    "10px",
                }}
              >
                {processing
                  ? "Processing..."
                  : "Approve"}
              </button>

              <button
                type="button"
                onClick={
                  handleReject
                }
                disabled={
                  processing
                }
                style={{
                  padding:
                    "9px 18px",
                  border: "none",
                  borderRadius:
                    "5px",
                  cursor:
                    processing
                      ? "not-allowed"
                      : "pointer",
                }}
              >
                {processing
                  ? "Processing..."
                  : "Reject"}
              </button>
            </div>
          )}

          {/* ==================================================
              VERIFICATION HISTORY
              ================================================== */}

          <div
            style={{
              borderTop:
                "1px solid #ddd",
              paddingTop:
                "20px",
            }}
          >
            <h3
              style={{
                marginTop: 0,
                marginBottom:
                  "15px",
              }}
            >
              Verification History
            </h3>

            {historyLoading ? (
              <p>
                Loading verification
                history...
              </p>
            ) : verificationHistory.length ===
              0 ? (
              <p
                style={{
                  color: "#666",
                }}
              >
                No verification history
                found.
              </p>
            ) : (
              <div
                style={{
                  overflowX:
                    "auto",
                }}
              >
                <table
                  style={{
                    width: "100%",
                    borderCollapse:
                      "collapse",
                    fontSize:
                      "14px",
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        backgroundColor:
                          "#f5f5f5",
                      }}
                    >
                      <th
                        style={{
                          padding:
                            "10px",
                          border:
                            "1px solid #ddd",
                          textAlign:
                            "left",
                        }}
                      >
                        Reviewer
                      </th>

                      <th
                        style={{
                          padding:
                            "10px",
                          border:
                            "1px solid #ddd",
                          textAlign:
                            "center",
                        }}
                      >
                        Status
                      </th>

                      <th
                        style={{
                          padding:
                            "10px",
                          border:
                            "1px solid #ddd",
                          textAlign:
                            "left",
                        }}
                      >
                        Verified At
                      </th>

                      <th
                        style={{
                          padding:
                            "10px",
                          border:
                            "1px solid #ddd",
                          textAlign:
                            "left",
                        }}
                      >
                        Comments
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {verificationHistory.map(
                      (
                        verification
                      ) => (
                        <tr
                          key={
                            verification.id
                          }
                        >
                          <td
                            style={{
                              padding:
                                "10px",
                              border:
                                "1px solid #ddd",
                            }}
                          >
                            {verification.reviewer_name ||
                              verification.reviewer ||
                              "-"}
                          </td>

                          <td
                            style={{
                              padding:
                                "10px",
                              border:
                                "1px solid #ddd",
                              textAlign:
                                "center",
                            }}
                          >
                            <span
                              style={{
                                ...getStatusStyle(
                                  verification.status
                                ),
                                display:
                                  "inline-block",
                                padding:
                                  "4px 9px",
                                borderRadius:
                                  "10px",
                                fontSize:
                                  "11px",
                                fontWeight:
                                  "600",
                              }}
                            >
                              {getStatusLabel(
                                verification.status
                              )}
                            </span>
                          </td>

                          <td
                            style={{
                              padding:
                                "10px",
                              border:
                                "1px solid #ddd",
                            }}
                          >
                            {verification.verified_at ||
                              "-"}
                          </td>

                          <td
                            style={{
                              padding:
                                "10px",
                              border:
                                "1px solid #ddd",
                            }}
                          >
                            {verification.comments ||
                              "-"}
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
      )}

      {/* ==================================================
          FOOTER ACTIONS
          ================================================== */}

      <div
        style={{
          display: "flex",
          gap: "10px",
          marginTop: "10px",
        }}
      >
        <button
          type="button"
          onClick={fetchData}
          disabled={loading}
          style={{
            padding: "9px 16px",
            border:
              "1px solid #ccc",
            borderRadius:
              "5px",
            backgroundColor:
              "#fff",
            cursor: "pointer",
          }}
        >
          Refresh
        </button>

        <button
          type="button"
          onClick={() =>
            navigate(
              "/reviewer/travel-requests"
            )
          }
          style={{
            padding: "9px 16px",
            border:
              "1px solid #ccc",
            borderRadius:
              "5px",
            backgroundColor:
              "#fff",
            cursor: "pointer",
          }}
        >
          Back to Reviewer Requests
        </button>
      </div>

    </div>
  );
}

export default ReviewerTravelRequestDetails;