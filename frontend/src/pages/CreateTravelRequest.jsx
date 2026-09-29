import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

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

  const [loadingCountries, setLoadingCountries] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await apiClient.get("countries/");
        setCountries(response.data);
      } catch (error) {
        console.error(error);
        setError("Unable to load countries.");
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
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      const response = await apiClient.post(
        "travel-requests/",
        formData
      );

      console.log("Travel request created:", response.data);

      navigate("/dashboard");
    } catch (error) {
      console.error(error);

      if (error.response?.data) {
        setError(
          JSON.stringify(error.response.data)
        );
      } else {
        setError(
          "Unable to create travel request."
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingCountries) {
    return <p>Loading countries...</p>;
  }

  return (
    <div>
      <h1>Create Travel Request</h1>

      {error && (
        <p style={{ color: "red" }}>
          {error}
        </p>
      )}

      <form onSubmit={handleSubmit}>

        <div>
          <label>
            Destination Country
          </label>

          <select
            name="destination_country"
            value={formData.destination_country}
            onChange={handleChange}
            required
          >
            <option value="">
              Select Country
            </option>

            {countries.map((country) => (
              <option
                key={country.id}
                value={country.id}
              >
                {country.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label>
            Destination City
          </label>

          <input
            type="text"
            name="destination_city"
            value={formData.destination_city}
            onChange={handleChange}
            placeholder="Enter destination city"
            required
          />
        </div>

        <div>
          <label>
            Client
          </label>

          <input
            type="text"
            name="client"
            value={formData.client}
            onChange={handleChange}
            placeholder="Enter client name"
            required
          />
        </div>

        <div>
          <label>
            Project
          </label>

          <input
            type="text"
            name="project"
            value={formData.project}
            onChange={handleChange}
            placeholder="Enter project name"
            required
          />
        </div>

        <div>
          <label>
            Travel Type
          </label>

          <select
            name="travel_type"
            value={formData.travel_type}
            onChange={handleChange}
            required
          >
            <option value="" disabled>
              Select Travel Type
            </option>

            <option value="DOMESTIC">
              Domestic
            </option>

            <option value="INTERNATIONAL">
              International
            </option>
          </select>
        </div>

        <div>
          <label>
            Start Date
          </label>

          <input
            type="date"
            name="start_date"
            value={formData.start_date}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label>
            End Date
          </label>

          <input
            type="date"
            name="end_date"
            value={formData.end_date}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label>
            Purpose
          </label>

          <textarea
            name="purpose"
            value={formData.purpose}
            onChange={handleChange}
            placeholder="Enter purpose of travel"
            rows="5"
            required
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
        >
          {submitting
            ? "Creating..."
            : "Create Travel Request"}
        </button>

        <button
          type="button"
          onClick={() => navigate("/dashboard")}
        >
          Cancel
        </button>

      </form>
    </div>
  );
}

export default CreateTravelRequest;