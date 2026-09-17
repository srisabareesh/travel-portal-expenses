import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../api/client";

function UploadDocument() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [checklist, setChecklist] = useState([]);

  const [formData, setFormData] = useState({
    document_type: "",
    issue_date: "",
    expiry_date: "",
  });

  const [file, setFile] = useState(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // --------------------------------
  // Fetch Document Checklist
  // --------------------------------

  useEffect(() => {
    const fetchChecklist = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await apiClient.get(
          `travel-requests/${id}/documents/`
        );

        const checklistData = response.data;

        // Handle array response
        if (Array.isArray(checklistData)) {
          setChecklist(checklistData);
        }

        // Handle paginated response
        else if (Array.isArray(checklistData.results)) {
          setChecklist(checklistData.results);
        }

        // Handle { checklist: [...] } response
        else if (Array.isArray(checklistData.checklist)) {
          setChecklist(checklistData.checklist);
        }

        // Unexpected response
        else {
          console.error(
            "Unexpected checklist API response:",
            checklistData
          );

          setChecklist([]);
          setError(
            "Unable to read document requirements."
          );
        }
      } catch (error) {
        console.error(
          "Failed to load document checklist:",
          error
        );

        if (error.response?.status === 401) {
          setError(
            "Your session has expired. Please login again."
          );
        } else if (error.response?.status === 403) {
          setError(
            "You do not have permission to access this request."
          );
        } else if (error.response?.status === 404) {
          setError("Travel request not found.");
        } else {
          setError(
            "Unable to load document requirements."
          );
        }

        setChecklist([]);
      } finally {
        setLoading(false);
      }
    };

    fetchChecklist();
  }, [id]);

  // --------------------------------
  // Form Change
  // --------------------------------

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previousData) => ({
      ...previousData,
      [name]: value,
    }));
  };

  // --------------------------------
  // File Change
  // --------------------------------

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) {
      setFile(null);
      return;
    }

    const allowedTypes = [
      "application/pdf",
      "image/jpeg",
      "image/png",
    ];

    const maxSize = 10 * 1024 * 1024;

    if (!allowedTypes.includes(selectedFile.type)) {
      setError(
        "Only PDF, JPG, JPEG and PNG files are allowed."
      );
      setFile(null);
      return;
    }

    if (selectedFile.size > maxSize) {
      setError(
        "File size cannot exceed 10 MB."
      );
      setFile(null);
      return;
    }

    setError("");
    setFile(selectedFile);
  };

  // --------------------------------
  // Submit Upload
  // --------------------------------

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!formData.document_type) {
      setError("Please select a document type.");
      return;
    }

    if (!file) {
      setError("Please select a document file.");
      return;
    }

    setSubmitting(true);

    const uploadData = new FormData();

    uploadData.append(
      "document_type",
      formData.document_type
    );

    uploadData.append(
      "file",
      file
    );

    if (formData.issue_date) {
      uploadData.append(
        "issue_date",
        formData.issue_date
      );
    }

    if (formData.expiry_date) {
      uploadData.append(
        "expiry_date",
        formData.expiry_date
      );
    }

    try {
      const response = await apiClient.post(
        `travel-requests/${id}/documents/upload/`,
        uploadData
      );

      console.log(
        "Document uploaded:",
        response.data
      );

      setSuccess(
        "Document uploaded successfully."
      );

      setFormData({
        document_type: "",
        issue_date: "",
        expiry_date: "",
      });

      setFile(null);

      const fileInput =
        document.getElementById(
          "document-file"
        );

      if (fileInput) {
        fileInput.value = "";
      }

      setTimeout(() => {
        navigate(
          `/travel-requests/${id}`
        );
      }, 1000);
    } catch (error) {
      console.error(
        "Document upload failed:",
        error
      );

      if (error.response?.data) {
        const backendErrors =
          error.response.data;

        if (
          typeof backendErrors ===
          "object"
        ) {
          const messages =
            Object.entries(
              backendErrors
            )
              .map(
                ([field, messages]) => {
                  if (
                    Array.isArray(messages)
                  ) {
                    return `${field}: ${messages.join(
                      ", "
                    )}`;
                  }

                  return `${field}: ${messages}`;
                }
              )
              .join(" | ");

          setError(messages);
        } else {
          setError(
            "Unable to upload document."
          );
        }
      } else {
        setError(
          "Unable to upload document."
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  // --------------------------------
  // Loading
  // --------------------------------

  if (loading) {
    return (
      <div
        style={{
          padding: "30px",
        }}
      >
        <h1>Upload Document</h1>

        <p>
          Loading document requirements...
        </p>
      </div>
    );
  }

  // --------------------------------
  // Error when checklist unavailable
  // --------------------------------

  if (
    error &&
    checklist.length === 0
  ) {
    return (
      <div
        style={{
          padding: "30px",
        }}
      >
        <p
          style={{
            color: "red",
          }}
        >
          {error}
        </p>

        <button
          onClick={() =>
            navigate(
              `/travel-requests/${id}`
            )
          }
        >
          Back to Travel Request
        </button>
      </div>
    );
  }

  // --------------------------------
  // Documents available for upload
  // --------------------------------

  const uploadableDocuments =
    checklist.filter(
      (document) =>
        document.status ===
          "MISSING" ||
        document.status ===
          "REJECTED"
    );

  // --------------------------------
  // Page
  // --------------------------------

  return (
    <div
      style={{
        maxWidth: "700px",
        margin: "0 auto",
        padding: "30px",
      }}
    >
      <h1>Upload Document</h1>

      <p>
        <strong>
          Travel Request ID:
        </strong>{" "}
        {id}
      </p>

      {error && (
        <p
          style={{
            color: "red",
          }}
        >
          {error}
        </p>
      )}

      {success && (
        <p
          style={{
            color: "green",
          }}
        >
          {success}
        </p>
      )}

      {uploadableDocuments.length ===
        0 ? (
        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "20px",
            marginBottom: "20px",
          }}
        >
          <p>
            There are no missing or rejected
            documents available for upload.
          </p>

          <button
            onClick={() =>
              navigate(
                `/travel-requests/${id}`
              )
            }
          >
            Back to Travel Request
          </button>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
        >
          {/* -------------------------------- */}
          {/* Document Type */}
          {/* -------------------------------- */}

          <div
            style={{
              marginBottom: "20px",
            }}
          >
            <label
              htmlFor="document_type"
            >
              <strong>
                Document Type
              </strong>
            </label>

            <br />

            <select
              id="document_type"
              name="document_type"
              value={
                formData.document_type
              }
              onChange={handleChange}
              required
              style={{
                marginTop: "8px",
                padding: "8px",
                minWidth: "300px",
              }}
            >
              <option value="">
                Select Document Type
              </option>

              {uploadableDocuments.map(
                (document) => (
                  <option
                    key={
                      document.document_type_id
                    }
                    value={
                      document.document_type_id
                    }
                  >
                    {document.document_type}

                    {document.status ===
                      "REJECTED"
                      ? " - Re-upload"
                      : ""}
                  </option>
                )
              )}
            </select>

            <p
              style={{
                fontSize: "13px",
                color: "#666",
                marginTop: "5px",
              }}
            >
              You can upload missing
              documents or replace
              documents rejected during
              review.
            </p>
          </div>

          {/* -------------------------------- */}
          {/* File */}
          {/* -------------------------------- */}

          <div
            style={{
              marginBottom: "20px",
            }}
          >
            <label htmlFor="document-file">
              <strong>
                Document File
              </strong>
            </label>

            <br />

            <input
              id="document-file"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={
                handleFileChange
              }
              required
              style={{
                marginTop: "8px",
              }}
            />

            <br />

            <small>
              Allowed: PDF, JPG, JPEG,
              PNG. Maximum 10 MB.
            </small>
          </div>

          {/* -------------------------------- */}
          {/* Issue Date */}
          {/* -------------------------------- */}

          <div
            style={{
              marginBottom: "20px",
            }}
          >
            <label htmlFor="issue_date">
              <strong>
                Issue Date
              </strong>
            </label>

            <br />

            <input
              id="issue_date"
              type="date"
              name="issue_date"
              value={
                formData.issue_date
              }
              onChange={handleChange}
              style={{
                marginTop: "8px",
                padding: "6px",
              }}
            />
          </div>

          {/* -------------------------------- */}
          {/* Expiry Date */}
          {/* -------------------------------- */}

          <div
            style={{
              marginBottom: "20px",
            }}
          >
            <label htmlFor="expiry_date">
              <strong>
                Expiry Date
              </strong>
            </label>

            <br />

            <input
              id="expiry_date"
              type="date"
              name="expiry_date"
              value={
                formData.expiry_date
              }
              onChange={handleChange}
              style={{
                marginTop: "8px",
                padding: "6px",
              }}
            />
          </div>

          {/* -------------------------------- */}
          {/* Buttons */}
          {/* -------------------------------- */}

          <div
            style={{
              display: "flex",
              gap: "10px",
            }}
          >
            <button
              type="submit"
              disabled={submitting}
            >
              {submitting
                ? "Uploading..."
                : "Upload Document"}
            </button>

            <button
              type="button"
              onClick={() =>
                navigate(
                  `/travel-requests/${id}`
                )
              }
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default UploadDocument;