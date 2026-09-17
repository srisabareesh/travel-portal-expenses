import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function ReviewerDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <div style={{ padding: "30px" }}>
      <h1>Reviewer Dashboard</h1>

      <p>
        Welcome,{" "}
        <strong>
          {user?.first_name || user?.username}
        </strong>
      </p>

      <p>
        Role: <strong>{user?.role}</strong>
      </p>

      <hr />

      <h2>Document Verification</h2>

      <p>
        Review travel requests and verify employee
        documents.
      </p>

      <button
        onClick={() =>
          navigate("/reviewer/travel-requests")
        }
      >
        Review Travel Requests
      </button>

      <br />
      <br />

      <button onClick={logout}>
        Logout
      </button>
    </div>
  );
}

export default ReviewerDashboard;