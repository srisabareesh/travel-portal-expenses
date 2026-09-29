import { useEffect, useState } from "react";
import apiClient from "../api/client";

import {
  LoadingState,
  EmptyState,
  Button,
} from "./ui";
import { formatDateTime } from "../lib/format";

/**
 * NotificationList — Phase 16.
 *
 * Renders the signed-in user's in-app notifications from
 * the backend notifications API, with mark-as-read.
 * `compact` trims the list for dashboard sidebars.
 */
export function NotificationList({ compact = false }) {
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
    return <LoadingState label="Loading notifications…" />;
  }

  if (error) {
    return (
      <div className="alert alert--error" role="alert">
        <span>{error}</span>
      </div>
    );
  }

  const visible = compact
    ? notifications.slice(0, 5)
    : notifications;

  if (notifications.length === 0) {
    return (
      <EmptyState
        icon="🔔"
        title="No notifications yet"
        description="Updates about your travel requests will appear here."
      />
    );
  }

  return (
    <div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {visible.map((notification) => (
          <li
            key={notification.id}
            className={`notif-item ${
              notification.is_read ? "read" : "unread"
            }`}
          >
            <span
              className="notif-dot"
              aria-hidden="true"
            />

            <div style={{ flex: 1, minWidth: 0 }}>
              <p className="notif-title">
                {notification.message}
              </p>

              <div className="notif-time">
                {formatDateTime(notification.created_at)}
              </div>
            </div>

            {!notification.is_read && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => markRead(notification.id)}
              >
                Mark read
              </Button>
            )}
          </li>
        ))}
      </ul>

      {compact && notifications.length > visible.length && (
        <p className="mt-1 mb-0 secondary">
          And {notifications.length - visible.length} more — see all
          notifications for the full list.
        </p>
      )}
    </div>
  );
}

export default NotificationList;
