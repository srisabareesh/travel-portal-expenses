import { useEffect, useState } from "react";
import apiClient from "../api/client";

import NotificationList from "../components/NotificationList";
import {
  PageHeader,
  Card,
  Tabs,
  EmptyState,
  InlineError,
  LoadingState,
} from "../components/ui";
import { roleLabel, formatDateTime } from "../lib/format";

function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("users");

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

      setLoading(false);
    };

    fetchData();
  }, []);

  const tabs = [
    { key: "users", label: "Users" },
    { key: "audit", label: "Audit Logs" },
    { key: "config", label: "Configuration" },
  ];

  return (
    <>
      <PageHeader
        title="Administration"
        description="Users, roles, and system configuration for the travel portal."
      />

      <InlineError>{loadError}</InlineError>

      <Tabs
        tabs={tabs}
        activeKey={activeTab}
        onChange={setActiveTab}
      />

      {loading ? (
        <LoadingState label="Loading administration data…" />
      ) : (
        <>
          {activeTab === "users" && (
            <Card title="Users" subtitle="Employee IDs and assigned roles." padded={false}>
              {users.length === 0 ? (
                <EmptyState
                  icon="👥"
                  title="No user list available"
                  description="User management is available through the Django admin console."
                />
              ) : (
                <div className="table-wrap" style={{ border: "none", boxShadow: "none" }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Employee ID</th>
                        <th>Username</th>
                        <th>Roles</th>
                      </tr>
                    </thead>

                    <tbody>
                      {users.map((item) => (
                        <tr key={item.id}>
                          <td className="cell-strong mono">{item.employee_id}</td>

                          <td>{item.username}</td>

                          <td>
                            <div className="flex" style={{ gap: 6 }}>
                              {(item.roles || []).map((role) => (
                                <span key={role} className="badge badge--neutral">
                                  {roleLabel(role)}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}

          {activeTab === "audit" && (
            <Card title="Recent audit logs" padded={false}>
              {auditLogs.length === 0 ? (
                <EmptyState
                  icon="🗂️"
                  title="No audit entries visible"
                  description="Audit logs will appear here as actions are recorded."
                />
              ) : (
                <div className="table-wrap" style={{ border: "none", boxShadow: "none" }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Action</th>
                        <th>Object</th>
                        <th>When</th>
                      </tr>
                    </thead>

                    <tbody>
                      {auditLogs.slice(0, 10).map((log) => (
                        <tr key={log.id}>
                          <td className="cell-strong">{log.action}</td>

                          <td>{log.object_repr}</td>

                          <td>{formatDateTime(log.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}

          {activeTab === "config" && (
            <Card
              title="Configuration"
              subtitle="Full configuration is managed through the Django admin console."
            >
              <p className="secondary">
                Countries, document types & requirements, expense rules, and
                system settings live in the Django admin.
              </p>

              <div className="btn-row">
                <a
                  href="http://127.0.0.1:8000/admin/"
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn--secondary"
                >
                  Open Django Admin ↗
                </a>
              </div>
            </Card>
          )}
        </>
      )}

      <div className="page-section">
        <Card
          title="Notifications"
          subtitle="System activity on your requests."
        >
          <NotificationList compact />
        </Card>
      </div>
    </>
  );
}

export default AdminDashboard;
