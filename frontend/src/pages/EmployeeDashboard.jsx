import { useAuth } from "../hooks/useAuth";
import { useNavigate } from "react-router-dom";

import NotificationList from "../components/NotificationList";

function EmployeeDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div>
      <h1>Onsite Travel Portal</h1>

      <h2>Employee Dashboard</h2>

      {user && (
        <div>
          <p>
            Welcome,{" "}
            <strong>
              {user.first_name} {user.last_name}
            </strong>
          </p>

          <p>
            Employee ID: {user.employee_id}
          </p>

          <p>
            Department: {user.department}
          </p>
        </div>
      )}

      <hr />

      <h3>Travel Management</h3>

      <div>
        <button
            onClick={() =>
            navigate("/travel-requests/create")
            }
        >
            Create Travel Request
        </button>

        <button
            onClick={() =>
            navigate("/travel-requests")
            }
        >
            My Travel Requests
        </button>
      </div>

      <hr />

      <NotificationList />

      <button onClick={logout}>
        Logout
      </button>
    </div>
  );
}

export default EmployeeDashboard;
