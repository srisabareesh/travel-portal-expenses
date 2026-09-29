import { useEffect, useState } from "react";
import apiClient from "../api/client";

/**
 * NotificationList — Phase 16.
 *
 * Renders the signed-in user's in-app notifications from
 * the backend notifications API, with mark-as-read.
 */
export function NotificationList() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchNotifications = async () => {
    try {
      const response = await apiClient.get("notifications/");

      setNotifications(response.data);
      setError("");
    } catch {
      setError("Unable to load notifications.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
          // eslint-disable-next-line react-hooks/set-state-in-effect -- loader sets state after await
      void fetchNotifications();
  }, []);



  const markRead = async (notificationId) => {
    try {
      await apiClient.post(
        `notifications/${notificationId}/read/`
      );

      await fetchNotifications();
    } catch {
      // Non-blocking: list refreshes on next visit.
    }
  };

  if (loading) {
    return <p>Loading notifications…</p>;
  }

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #ddd",
        borderRadius: "10px",
        padding: "20px",
        margin: "20px 0",
      }}
    >
      <h3 style={{ marginTop: 0 }}>
        Notifications
      </h3>

      {error && (
        <p style={{ color: "#c62828" }}>{error}</p>
      )}

      {notifications.length === 0 ? (
        <p>No notifications yet.</p>
      ) : (
        <ul style={{ paddingLeft: "16px" }}>
          {notifications.map((notification) => (
            <li
              key={notification.id}
              style={{
                marginBottom: "10px",
                fontWeight: notification.is_read
                  ? "normal"
                  : "bold",
              }}
            >
              <div>{notification.message}</div>

              <div
                style={{
                  color: "#777",
                  fontSize: "12px",
                }}
              >
                {new Date(
                  notification.created_at
                ).toLocaleString()}
                {!notification.is_read && (
                  <button
                    style={{ marginLeft: "10px" }}
                    onClick={() =>
                      markRead(notification.id)
                    }
                  >
                    Mark read
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default NotificationList;
