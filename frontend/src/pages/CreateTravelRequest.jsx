import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import apiClient from "../api/client";

import {
  PageHeader,
  Card,
  Button,
  FormField,
  InlineError,
  Breadcrumb,
  LoadingState,
} from "../components/ui";
import { extractApiError } from "../lib/format";

function CreateTravelRequest() {
  const navigate = useNavigate();

  const [countries, setCountries] = useState([]);

  const [formData, setFormData] = useState({
    destination_country: "",
    destination_city: "",
    client: "",
    project: "",
    travel_type: "",
    start_date: "",
    end_date: "",
    purpose: "",
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");

  const [loadingCountries, setLoadingCountries] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await apiClient.get("countries/");
        setCountries(response.data);
      } catch (err) {
        setError(extractApiError(err, "Unable to load countries."));
      } finally {
        setLoadingCountries(false);
      }
    };

    fetchCountries();
  }, []);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previousData) => ({
      ...previousData,
      [name]: value,
    }));

    setFieldErrors((previous) => ({
      ...previous,
      [name]: undefined,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setFieldErrors({});
    setSubmitting(true);

    try {
      await apiClient.post(
        "travel-requests/",
        formData
      );

      navigate("/dashboard");
    } catch (err) {
      const data = err.response?.data;

      if (data && typeof data === "object") {
        const fieldErrors = {};
        let firstGlobal = "";

        Object.entries(data).forEach(([field, messages]) => {
          if (Array.isArray(messages) && messages.length > 0) {
            fieldErrors[field] = messages.join(" ");
          } else if (typeof messages === "string" && field === "detail") {
            firstGlobal = messages;
          }
        });

        setFieldErrors(fieldErrors);

        if (firstGlobal) {
          setError(firstGlobal);
        } else if (Object.keys(fieldErrors).length > 0) {
          setError("Please correct the highlighted fields.");
        } else {
          setError(extractApiError(err, "Unable to create travel request."));
        }
      } else {
        setError(extractApiError(err, "Unable to create travel request."));
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingCountries) {
    return (
      <>
        <PageHeader
          title="Create Travel Request"
          description="Tell us about the trip and submit it for approval."
        />
        <LoadingState label="Loading countries…" />
      </>
    );
  }

  return (
    <>
      <Breadcrumb
        items={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Travel Requests", to: "/travel-requests" },
          { label: "Create" },
        ]}
      />

      <PageHeader
        title="Create Travel Request"
        description="Tell us about the trip and submit it for approval."
      />

      <InlineError>{error}</InlineError>

      <form onSubmit={handleSubmit} noValidate>
        <Card title="Travel details" subtitle="All fields are required.">
          <div className="form-grid">
            <FormField
              label="Travel Type"
              htmlFor="travel_type"
              required
              error={fieldErrors.travel_type}
            >
              <select
                id="travel_type"
                name="travel_type"
                className="select"
                value={formData.travel_type}
                onChange={handleChange}
                required
              >
                <option value="" disabled>
                  Select travel type
                </option>
                <option value="DOMESTIC">Domestic</option>
                <option value="INTERNATIONAL">International</option>
              </select>
            </FormField>

            <FormField
              label="Destination Country"
              htmlFor="destination_country"
              required
              error={fieldErrors.destination_country}
            >
              <select
                id="destination_country"
                name="destination_country"
                className="select"
                value={formData.destination_country}
                onChange={handleChange}
                required
              >
                <option value="">Select country</option>

                {countries.map((country) => (
                  <option
                    key={country.id}
                    value={country.id}
                  >
                    {country.name}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField
              label="Destination City"
              htmlFor="destination_city"
              required
              error={fieldErrors.destination_city}
            >
              <input
                id="destination_city"
                className="input"
                type="text"
                name="destination_city"
                value={formData.destination_city}
                onChange={handleChange}
                placeholder="e.g. Bengaluru"
                required
              />
            </FormField>

            <FormField
              label="Client"
              htmlFor="client"
              required
              error={fieldErrors.client}
            >
              <input
                id="client"
                className="input"
                type="text"
                name="client"
                value={formData.client}
                onChange={handleChange}
                placeholder="Client name"
                required
              />
            </FormField>

            <FormField
              label="Project"
              htmlFor="project"
              required
              error={fieldErrors.project}
            >
              <input
                id="project"
                className="input"
                type="text"
                name="project"
                value={formData.project}
                onChange={handleChange}
                placeholder="Project name"
                required
              />
            </FormField>

            <FormField
              label="Start Date"
              htmlFor="start_date"
              required
              error={fieldErrors.start_date}
            >
              <input
                id="start_date"
                className="input"
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleChange}
                required
              />
            </FormField>

            <FormField
              label="End Date"
              htmlFor="end_date"
              required
              error={fieldErrors.end_date}
              help="Must be on or after the start date."
            >
              <input
                id="end_date"
                className="input"
                type="date"
                name="end_date"
                value={formData.end_date}
                onChange={handleChange}
                required
              />
            </FormField>

            <div className="form-field--full">
              <FormField
                label="Purpose of Travel"
                htmlFor="purpose"
                required
                error={fieldErrors.purpose}
              >
                <textarea
                  id="purpose"
                  className="textarea"
                  name="purpose"
                  value={formData.purpose}
                  onChange={handleChange}
                  placeholder="Describe the purpose of this trip"
                  rows={4}
                  required
                />
              </FormField>
            </div>
          </div>
        </Card>

        <div className="btn-row mt-2">
          <Button type="submit" variant="primary" size="lg" loading={submitting}>
            {submitting ? "Creating…" : "Create Travel Request"}
          </Button>

          <Link to="/dashboard" className="btn btn--secondary">
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}

export default CreateTravelRequest;
