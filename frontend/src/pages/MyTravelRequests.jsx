import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

function MyTravelRequests() {
  const navigate = useNavigate();

  const [travelRequests, setTravelRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchTravelRequests = async () => {
      try {
        const response = await apiClient.get(
          "travel-requests/"
        );

        setTravelRequests(response.data);
      } catch (error) {
        console.error(error);
        setError(
          "Unable to load travel requests."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchTravelRequests();
  }, []);

  if (loading) {
    return <p>Loading travel requests...</p>;
  }

  return (
    <div>
      <h1>My Travel Requests</h1>

      {error && (
        <p style={{ color: "red" }}>
          {error}
        </p>
      )}

      {travelRequests.length === 0 ? (
        <div>
          <p>
            You have not created any travel requests yet.
          </p>

          <button
            onClick={() =>
              navigate("/travel-requests/create")
            }
          >
            Create Travel Request
          </button>
        </div>
      ) : (
        <div>
          {travelRequests.map((request) => (
            <div
              key={request.id}
              style={{
                border: "1px solid #ccc",
                padding: "15px",
                marginBottom: "15px",
                borderRadius: "8px",
              }}
            >
              <h3>
                {request.request_number}
              </h3>

              <p>
                <strong>Destination:</strong>{" "}
                {request.country_name},{" "}
                {request.destination_city}
              </p>

              <p>
                <strong>Client:</strong>{" "}
                {request.client}
              </p>

              <p>
                <strong>Project:</strong>{" "}
                {request.project}
              </p>

              <p>
                <strong>Travel Type:</strong>{" "}
                {request.travel_type}
              </p>

              <p>
                <strong>Start Date:</strong>{" "}
                {request.start_date}
              </p>

              <p>
                <strong>End Date:</strong>{" "}
                {request.end_date}
              </p>

              <p>
                <strong>Status:</strong>{" "}
                {request.status}
              </p>

              <button
                onClick={() =>
                  navigate(
                    `/travel-requests/${request.id}`
                  )
                }
              >
                View Details
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => navigate("/dashboard")}
      >
        Back to Dashboard
      </button>
    </div>
  );
}

export default MyTravelRequests;