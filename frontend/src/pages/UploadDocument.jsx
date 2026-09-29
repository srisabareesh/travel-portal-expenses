import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import apiClient from "../api/client";

import {
  PageHeader,
  Breadcrumb,
  Card,
  Button,
  FormField,
  LoadingState,
  ErrorState,
  InlineError,
  EmptyState,
  DocumentStatusBadge,
} from "../components/ui";
import { extractApiError } from "../lib/format";

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

  /* --------------------------------
     Fetch Document Checklist
     -------------------------------- */

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
          setChecklist([]);
          setError(
            "Unable to read document requirements."
          );
        }
      } catch (err) {
        if (err.response?.status === 401) {
          setError(
            "Your session has expired. Please login again."
          );
        } else if (err.response?.status === 403) {
          setError(
            "You do not have permission to access this request."
          );
        } else if (err.response?.status === 404) {
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

  /* --------------------------------
     Form Change
     -------------------------------- */

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previousData) => ({
      ...previousData,
      [name]: value,
    }));
  };

  /* --------------------------------
     File Change
     -------------------------------- */

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

  /* --------------------------------
     Submit Upload
     -------------------------------- */

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
      await apiClient.post(
        `travel-requests/${id}/documents/upload/`,
        uploadData
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
    } catch (err) {
      setError(
        extractApiError(err, "Unable to upload document.")
      );
    } finally {
      setSubmitting(false);
    }
  };

  /* --------------------------------
     Loading
     -------------------------------- */

  if (loading) {
    return (
      <>
        <PageHeader
          title="Upload Document"
          description="Provide the required travel documents."
        />
        <LoadingState label="Loading document requirements…" />
      </>
    );
  }

  /* --------------------------------
     Error when checklist unavailable
     -------------------------------- */

  if (error && checklist.length === 0) {
    return (
      <>
        <Breadcrumb
          items={[
            { label: "Travel Requests", to: "/travel-requests" },
            { label: `#${id}`, to: `/travel-requests/${id}` },
            { label: "Upload Document" },
          ]}
        />
        <ErrorState
          title="Unable to load document requirements"
          message={error}
          onRetry={() => navigate(`/travel-requests/${id}`)}
        />
      </>
    );
  }

  /* --------------------------------
     Documents available for upload
     -------------------------------- */

  const uploadableDocuments =
    checklist.filter(
      (document) =>
        document.status === "MISSING" ||
        document.status === "REJECTED"
    );

  /* --------------------------------
     Page
     -------------------------------- */

  return (
    <>
      <Breadcrumb
        items={[
          { label: "Travel Requests", to: "/travel-requests" },
          { label: `#${id}`, to: `/travel-requests/${id}` },
          { label: "Upload Document" },
        ]}
      />

      <PageHeader
        title="Upload Document"
        description="Provide a missing document or replace one that was rejected."
      />

      <InlineError>{error}</InlineError>

      {success && (
        <div className="alert alert--success" role="status">
          <span>{success} Redirecting you back to the request…</span>
        </div>
      )}

      {uploadableDocuments.length === 0 ? (
        <Card>
          <EmptyState
            icon="📎"
            title="Nothing to upload right now"
            description="There are no missing or rejected documents available for upload on this request."
            action={
              <Link
                to={`/travel-requests/${id}`}
                className="btn btn--secondary"
              >
                Back to Travel Request
              </Link>
            }
          />
        </Card>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <Card title="Document details">
            <div className="stack">
              <FormField
                label="Document Type"
                htmlFor="document_type"
                required
                help="You can upload missing documents or replace documents rejected during review."
              >
                <select
                  id="document_type"
                  name="document_type"
                  className="select"
                  value={formData.document_type}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select document type</option>

                  {uploadableDocuments.map((document) => (
                    <option
                      key={document.document_type_id}
                      value={document.document_type_id}
                    >
                      {document.document_type}
                      {document.status === "REJECTED"
                        ? " — Re-upload"
                        : ""}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField
                label="File"
                htmlFor="document-file"
                required
                help="PDF, JPG or PNG, up to 10 MB."
              >
                <input
                  id="document-file"
                  className="input"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleFileChange}
                  required
                />
              </FormField>

              <div className="form-grid">
                <FormField
                  label="Issue Date (optional)"
                  htmlFor="issue_date"
                >
                  <input
                    id="issue_date"
                    className="input"
                    type="date"
                    name="issue_date"
                    value={formData.issue_date}
                    onChange={handleChange}
                  />
                </FormField>

                <FormField
                  label="Expiry Date (optional)"
                  htmlFor="expiry_date"
                >
                  <input
                    id="expiry_date"
                    className="input"
                    type="date"
                    name="expiry_date"
                    value={formData.expiry_date}
                    onChange={handleChange}
                  />
                </FormField>
              </div>
            </div>
          </Card>

          <div className="btn-row mt-2">
            <Button type="submit" variant="primary" loading={submitting}>
              {submitting ? "Uploading…" : "Upload Document"}
            </Button>

            <Link
              to={`/travel-requests/${id}`}
              className="btn btn--secondary"
            >
              Cancel
            </Link>
          </div>
        </form>
      )}

      {/* Checklist context */}
      {checklist.length > 0 && (
        <Card title="Document checklist" className="mt-3" padded={false}>
          <div className="table-wrap" style={{ border: "none", boxShadow: "none" }}>
            <table className="table table--compact">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {checklist.map((document) => (
                  <tr key={document.document_type_id}>
                    <td className="cell-strong">
                      {document.document_type || "—"}
                    </td>
                    <td>
                      <DocumentStatusBadge status={document.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}

export default UploadDocument;
