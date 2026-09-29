import { useAuth } from "../hooks/useAuth";

function Dashboard() {
  const { user, logout, loading } = useAuth();

  if (loading) {
    return <p>Loading...</p>;
  }

  return (
    <div>
      <h1>Onsite Travel Portal</h1>

      <h2>Dashboard</h2>

      {user && (
        <div>
          <p>
            <strong>Username:</strong>{" "}
            {user.username}
          </p>

          <p>
            <strong>Employee ID:</strong>{" "}
            {user.employee_id}
          </p>

          <p>
            <strong>Department:</strong>{" "}
            {user.department}
          </p>

          <p>
            <strong>Role:</strong>{" "}
            {user.role}
          </p>
        </div>
      )}

      <button onClick={logout}>
        Logout
      </button>
    </div>
  );
}

export default Dashboard;