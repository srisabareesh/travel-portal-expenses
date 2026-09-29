import { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import apiClient from "../api/client";

import NotificationList from "../components/NotificationList";

function AdminDashboard() {
  const { user, logout } = useAuth();

  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      const results = await Promise.allSettled([
        apiClient.get("admin-users/"),
        apiClient.get("admin-audit-logs/"),
      ]);

      if (results[0].status === "fulfilled") {
        setUsers(results[0].value.data);
      }

      if (results[1].status === "fulfilled") {
        setAuditLogs(results[1].value.data);
      }

      if (
        results[0].status === "rejected" &&
        results[1].status === "rejected"
      ) {
        setLoadError(
          "Administrator list APIs are not enabled yet. Use the Django admin for full configuration."
        );
      }
    };

    fetchData();
  }, []);

  return (
    <div style={{ padding: "30px" }}>
      <h1>Admin Dashboard</h1>

      {user && (
        <p>
          Signed in as{" "}
          <strong>{user.username}</strong> (administrator)
        </p>
      )}

      <p>
        Administrative configuration is managed through the
        Django admin console:
      </p>

      <ul>
        <li>
          <a
            href="http://127.0.0.1:8000/admin/"
            target="_blank"
            rel="noreferrer"
          >
            Django Admin — users, roles, countries,
            document types & requirements, expense data,
            system configuration, audit logs
          </a>
        </li>
      </ul>

      {loadError && (
        <p style={{ color: "#8a6500" }}>{loadError}</p>
      )}

      <div
        style={{
          display: "flex",
          gap: "20px",
          flexWrap: "wrap",
          marginTop: "20px",
        }}
      >
        <div
          style={{
            flex: "1 1 300px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "20px",
          }}
        >
          <h3>Users ({users.length})</h3>

          {users.length === 0 ? (
            <p>No user list available.</p>
          ) : (
            <table style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th align="left">Employee ID</th>
                  <th align="left">Username</th>
                  <th align="left">Roles</th>
                </tr>
              </thead>

              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td>{item.employee_id}</td>

                    <td>{item.username}</td>

                    <td>
                      {(item.roles || []).join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div
          style={{
            flex: "1 1 300px",
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "20px",
          }}
        >
          <h3>Recent Audit Logs</h3>

          {auditLogs.length === 0 ? (
            <p>No audit entries visible.</p>
          ) : (
            auditLogs.slice(0, 10).map((log) => (
              <p key={log.id}>
                <strong>{log.action}</strong> —{" "}
                {log.object_repr} (
                {new Date(
                  log.created_at
                ).toLocaleString()}
                )
              </p>
            ))
          )}
        </div>
      </div>

      <NotificationList />

      <button onClick={logout}>Logout</button>
    </div>
  );
}

export default AdminDashboard;
