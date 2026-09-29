import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import apiClient from "../api/client";

import WorkflowProgress from "../components/WorkflowProgress";
import TravelSections from "../components/TravelSections";


function ManagerTravelRequestDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [travelRequest, setTravelRequest] = useState(null);
  const [checklist, setChecklist] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);

  const [rejectionComments, setRejectionComments] =
    useState("");

  const [showRejectForm, setShowRejectForm] =
    useState(false);


  const loadDetails = async () => {
    try {
      setLoading(true);
      setError("");

      const requestResponse = await apiClient.get(
        `travel-requests/${id}/`
      );

      const checklistResponse = await apiClient.get(
        `travel-requests/${id}/documents/`
      );

      setTravelRequest(requestResponse.data);

      const checklistData = checklistResponse.data;

      if (Array.isArray(checklistData)) {
        setChecklist(checklistData);
      } else if (
        Array.isArray(checklistData.checklist)
      ) {
        setChecklist(checklistData.checklist);
      } else if (
        Array.isArray(checklistData.results)
      ) {
        setChecklist(checklistData.results);
      } else {
        setChecklist([]);
      }

    } catch (err) {
      console.error(
        "Failed to load travel request details:",
        err
      );

      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(
          "Failed to load travel request details."
        );
      }
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
    void loadDetails();
  }, [id]);


  /*
   * Document verification summary
   */

  const totalDocuments = checklist.length;

  const verifiedDocuments = checklist.filter(
    (document) =>
      document.status === "VERIFIED"
  ).length;

  const pendingDocuments = checklist.filter(
    (document) =>
      document.status === "UPLOADED" ||
      document.status === "PENDING_REVIEW" ||
      document.status === "EXPIRING_SOON"
  ).length;

  const rejectedDocuments = checklist.filter(
    (document) =>
      document.status === "REJECTED"
  ).length;

  const missingDocuments = checklist.filter(
    (document) =>
      document.status === "MISSING"
  ).length;

  const mandatoryDocuments = checklist.filter(
    (document) =>
      document.mandatory === true
  ).length;

  const verifiedMandatoryDocuments =
    checklist.filter(
      (document) =>
        document.mandatory === true &&
        document.status === "VERIFIED"
    ).length;

  const allMandatoryVerified =
    mandatoryDocuments === 0 ||
    verifiedMandatoryDocuments ===
      mandatoryDocuments;


  /*
   * Manager approval
   */

  const approveTravelRequest = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to approve this travel request?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setProcessing(true);
      setError("");

      const response = await apiClient.post(
        `travel-requests/${id}/approve/`
      );

      setTravelRequest(response.data);

    } catch (err) {
      console.error(
        "Failed to approve travel request:",
        err
      );

      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(
          "Failed to approve travel request."
        );
      }
    } finally {
      setProcessing(false);
    }
  };


  /*
   * Show rejection form
   */

  const openRejectForm = () => {
    setError("");
    setRejectionComments("");
    setShowRejectForm(true);
  };


  /*
   * Cancel rejection
   */

  const cancelRejectForm = () => {
    if (processing) {
      return;
    }

    setShowRejectForm(false);
    setRejectionComments("");
    setError("");
  };


  /*
   * Manager rejection
   */

  const rejectTravelRequest = async () => {

    if (!rejectionComments.trim()) {
      setError(
        "Rejection comments are required."
      );
      return;
    }

    const confirmed = window.confirm(
      "Are you sure you want to reject this travel request?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setProcessing(true);
      setError("");

      const response = await apiClient.post(
        `travel-requests/${id}/reject/`,
        {
          comments:
            rejectionComments.trim(),
        }
      );

      setTravelRequest(response.data);

      setShowRejectForm(false);
      setRejectionComments("");

    } catch (err) {
      console.error(
        "Failed to reject travel request:",
        err
      );

      if (err.response?.data?.comments) {
        setError(
          err.response.data.comments
        );
      } else if (err.response?.data?.detail) {
        setError(
          err.response.data.detail
        );
      } else {
        setError(
          "Failed to reject travel request."
        );
      }
    } finally {
      setProcessing(false);
    }
  };


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


  const getDocumentStatusLabel = (status) => {
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
      case "APPROVED":
        return {
          backgroundColor: "#e8f5e9",
          color: "#2e7d32",
        };

      case "PENDING_REVIEW":
      case "UPLOADED":
      case "DOCUMENT_VERIFICATION":
        return {
          backgroundColor: "#fff4d6",
          color: "#8a6500",
        };

      case "MISSING":
      case "REJECTED":
        return {
          backgroundColor: "#ffebee",
          color: "#c62828",
        };

      case "DOCUMENT_PENDING":
        return {
          backgroundColor: "#fff4d6",
          color: "#8a6500",
        };

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
          maxWidth: "1100px",
          margin: "40px auto",
          padding: "20px",
        }}
      >
        <h1>
          Manager Travel Request Details
        </h1>

        <p>
          Loading travel request...
        </p>
      </div>
    );
  }


  if (error && !travelRequest) {
    return (
      <div
        style={{
          maxWidth: "1100px",
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

          <h1>
            Manager Travel Request Details
          </h1>

          <div
            style={{
              backgroundColor: "#ffebee",
              border: "1px solid #ef9a9a",
              borderRadius: "6px",
              padding: "12px",
              color: "#c62828",
              marginBottom: "20px",
            }}
          >
            {error}
          </div>

          <button
            onClick={() =>
              navigate(
                "/manager/travel-requests"
              )
            }
          >
            Back to Travel Requests
          </button>

        </div>

      </div>
    );
  }


  if (!travelRequest) {
    return null;
  }


  return (
    <div
      style={{
        maxWidth: "1100px",
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

        {/* Header */}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "15px",
            flexWrap: "wrap",
            marginBottom: "25px",
          }}
        >

          <div>

            <h1
              style={{
                marginTop: 0,
                marginBottom: "8px",
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
              Review the travel request information
              and document status.
            </p>

          </div>


          <div
            style={{
              display: "flex",
              gap: "10px",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >

            {travelRequest.status ===
              "DOCUMENT_VERIFICATION" &&
              allMandatoryVerified && (
                <button
                  onClick={approveTravelRequest}
                  disabled={processing}
                >
                  {processing
                    ? "Approving..."
                    : "Approve Travel Request"}
                </button>
              )}


            {travelRequest.status ===
              "DOCUMENT_VERIFICATION" && (
                <button
                  onClick={openRejectForm}
                  disabled={processing}
                >
                  Reject Travel Request
                </button>
              )}


            <button
              onClick={() =>
                navigate(
                  "/manager/travel-requests"
                )
              }
              disabled={processing}
            >
              Back to Travel Requests
            </button>

          </div>

        </div>


        {/* Error message */}

        {error && (
          <div
            style={{
              backgroundColor: "#ffebee",
              border: "1px solid #ef9a9a",
              borderRadius: "6px",
              padding: "12px",
              color: "#c62828",
              marginBottom: "20px",
            }}
          >
            {error}
          </div>
        )}


        {/* Rejection Form */}

        {showRejectForm && (
          <div
            style={{
              border: "1px solid #ef9a9a",
              borderRadius: "8px",
              padding: "20px",
              marginBottom: "25px",
              backgroundColor: "#fffafa",
            }}
          >

            <h2
              style={{
                marginTop: 0,
                marginBottom: "10px",
              }}
            >
              Reject Travel Request
            </h2>


            <p
              style={{
                color: "#666",
                marginTop: 0,
              }}
            >
              Please provide a reason for rejecting
              this travel request.
            </p>


            <label
              htmlFor="rejectionComments"
              style={{
                display: "block",
                fontWeight: "600",
                marginBottom: "8px",
              }}
            >
              Rejection Comments
            </label>


            <textarea
              id="rejectionComments"
              value={rejectionComments}
              onChange={(event) =>
                setRejectionComments(
                  event.target.value
                )
              }
              placeholder="Enter the reason for rejection..."
              rows={5}
              disabled={processing}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "12px",
                border: "1px solid #ccc",
                borderRadius: "6px",
                resize: "vertical",
                fontFamily: "inherit",
                fontSize: "14px",
              }}
            />


            <div
              style={{
                marginTop: "15px",
                display: "flex",
                gap: "10px",
                flexWrap: "wrap",
              }}
            >

              <button
                onClick={rejectTravelRequest}
                disabled={processing}
              >
                {processing
                  ? "Rejecting..."
                  : "Confirm Rejection"}
              </button>


              <button
                onClick={cancelRejectForm}
                disabled={processing}
              >
                Cancel
              </button>

            </div>

          </div>
        )}


        {/* Travel Request Information */}

        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "25px",
            marginBottom: "25px",
          }}
        >

          <h2
            style={{
              marginTop: 0,
              marginBottom: "20px",
            }}
          >
            Travel Request Information
          </h2>


          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(250px, 1fr))",
              gap: "20px",
            }}
          >

            <div>
              <strong>
                Request Number
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.request_number ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                Employee
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.employee_name ||
                  travelRequest.employee ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                Destination Country
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.country_name ||
                  travelRequest.destination_country ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                Destination City
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.destination_city ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                Travel Type
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.travel_type ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                Start Date
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.start_date ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                End Date
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.end_date ||
                  "-"}
              </div>
            </div>


            <div>
              <strong>
                Status
              </strong>

              <div style={{ marginTop: "8px" }}>

                <span
                  style={{
                    ...getStatusStyle(
                      travelRequest.status
                    ),
                    display: "inline-block",
                    padding: "5px 10px",
                    borderRadius: "12px",
                    fontSize: "13px",
                    fontWeight: "600",
                  }}
                >
                  {getStatusLabel(
                    travelRequest.status
                  )}
                </span>

              </div>
            </div>


            <div>
              <strong>
                Client
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.client || "-"}
              </div>
            </div>


            <div>
              <strong>
                Project
              </strong>

              <div style={{ marginTop: "5px" }}>
                {travelRequest.project || "-"}
              </div>
            </div>

          </div>


          <div
            style={{
              marginTop: "25px",
            }}
          >

            <strong>
              Purpose
            </strong>

            <div
              style={{
                marginTop: "8px",
                padding: "15px",
                backgroundColor: "#f8f8f8",
                borderRadius: "6px",
                whiteSpace: "pre-wrap",
              }}
            >
              {travelRequest.purpose || "-"}
            </div>

          </div>

        </div>


        {/* Document Verification Summary */}

        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "25px",
            marginBottom: "25px",
          }}
        >

          <h2
            style={{
              marginTop: 0,
              marginBottom: "20px",
            }}
          >
            Document Verification Summary
          </h2>


          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(170px, 1fr))",
              gap: "15px",
            }}
          >

            {/* Total Documents */}

            <div
              style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "18px",
                textAlign: "center",
              }}
            >

              <div
                style={{
                  fontSize: "28px",
                  fontWeight: "700",
                }}
              >
                {totalDocuments}
              </div>

              <div
                style={{
                  marginTop: "5px",
                  color: "#666",
                }}
              >
                Total Documents
              </div>

            </div>


            {/* Verified */}

            <div
              style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "18px",
                textAlign: "center",
              }}
            >

              <div
                style={{
                  fontSize: "28px",
                  fontWeight: "700",
                }}
              >
                {verifiedDocuments}
              </div>

              <div
                style={{
                  marginTop: "5px",
                  color: "#2e7d32",
                  fontWeight: "600",
                }}
              >
                Verified
              </div>

            </div>


            {/* Pending Review */}

            <div
              style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "18px",
                textAlign: "center",
              }}
            >

              <div
                style={{
                  fontSize: "28px",
                  fontWeight: "700",
                }}
              >
                {pendingDocuments}
              </div>

              <div
                style={{
                  marginTop: "5px",
                  color: "#8a6500",
                  fontWeight: "600",
                }}
              >
                Pending Review
              </div>

            </div>


            {/* Rejected */}

            <div
              style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "18px",
                textAlign: "center",
              }}
            >

              <div
                style={{
                  fontSize: "28px",
                  fontWeight: "700",
                }}
              >
                {rejectedDocuments}
              </div>

              <div
                style={{
                  marginTop: "5px",
                  color: "#c62828",
                  fontWeight: "600",
                }}
              >
                Rejected
              </div>

            </div>


            {/* Missing */}

            <div
              style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "18px",
                textAlign: "center",
              }}
            >

              <div
                style={{
                  fontSize: "28px",
                  fontWeight: "700",
                }}
              >
                {missingDocuments}
              </div>

              <div
                style={{
                  marginTop: "5px",
                  color: "#c62828",
                  fontWeight: "600",
                }}
              >
                Missing
              </div>

            </div>

          </div>


          {/* Mandatory document result */}

          <div
            style={{
              marginTop: "20px",
              padding: "15px",
              borderRadius: "6px",
              backgroundColor:
                allMandatoryVerified
                  ? "#e8f5e9"
                  : "#fff4d6",
              color:
                allMandatoryVerified
                  ? "#2e7d32"
                  : "#8a6500",
              fontWeight: "600",
            }}
          >
            {allMandatoryVerified
              ? "All mandatory documents are verified."
              : "All mandatory documents are not yet verified."}
          </div>

        </div>


        {/* Document Status */}

        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "25px",
          }}
        >

          <h2
            style={{
              marginTop: 0,
              marginBottom: "20px",
            }}
          >
            Document Status
          </h2>


          {checklist.length === 0 ? (

            <div
              style={{
                padding: "20px",
                textAlign: "center",
                color: "#666",
                border: "1px solid #ddd",
                borderRadius: "6px",
              }}
            >
              No document requirements found.
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
                  minWidth: "700px",
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
                      Document
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
                        textAlign: "left",
                      }}
                    >
                      Status
                    </th>

                    <th
                      style={{
                        padding: "12px",
                        border: "1px solid #ddd",
                        textAlign: "left",
                      }}
                    >
                      Issue Date
                    </th>

                    <th
                      style={{
                        padding: "12px",
                        border: "1px solid #ddd",
                        textAlign: "left",
                      }}
                    >
                      Expiry Date
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {checklist.map(
                    (document) => (

                      <tr
                        key={
                          document.document_type_id
                        }
                      >

                        <td
                          style={{
                            padding: "12px",
                            border: "1px solid #ddd",
                            fontWeight: "600",
                          }}
                        >
                          {
                            document.document_type
                          }
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
                                "13px",
                              fontWeight:
                                "600",
                            }}
                          >
                            {
                              getDocumentStatusLabel(
                                document.status
                              )
                            }
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

                      </tr>

                    )
                  )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      </div>

      <WorkflowProgress
        travelRequestId={id}
      />

      <TravelSections travelRequestId={id} />

    </div>
  );
}


export default ManagerTravelRequestDetails;