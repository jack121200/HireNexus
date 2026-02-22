import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch } from "../../lib/api";

type Notification = {
  id: number;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
};

type NotificationsResponse = {
  items: Notification[];
  unread_count: number;
};

export const HrNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = () => {
    apiFetch<NotificationsResponse>("/api/hr/notifications")
      .then((data) => {
        setNotifications(data.items);
        setUnread(data.unread_count);
      })
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const markRead = async (id: number) => {
    try {
      const data = await apiFetch<{ unread_count: number }>(`/api/hr/notifications/${id}/read`, {
        method: "POST",
      });
      setUnread(data.unread_count);
      loadNotifications();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const markAll = async () => {
    try {
      const data = await apiFetch<{ unread_count: number }>(`/api/hr/notifications/mark-all-read`, {
        method: "POST",
      });
      setUnread(data.unread_count);
      loadNotifications();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="HR Suite"
        title="Notifications"
        subtitle="Stay on top of applications, interviews, and candidate updates."
        actions={
          <Button variant="secondary" onClick={markAll}>
            Mark all read ({unread})
          </Button>
        }
      />
      {error && <p className="text-danger">{error}</p>}
      {notifications.length === 0 && (
        <EmptyState title="No notifications" description="Updates will appear here as they arrive." />
      )}
      <div className="space-y-3">
        {notifications.map((notification) => (
          <Card key={notification.id} variant="muted" className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-white">{notification.title}</div>
              {!notification.is_read && (
                <Button variant="ghost" size="sm" onClick={() => markRead(notification.id)}>
                  Mark read
                </Button>
              )}
            </div>
            <p className="text-sm text-textMuted">{notification.body}</p>
            <div className="text-xs text-textMuted">{new Date(notification.created_at).toLocaleString()}</div>
          </Card>
        ))}
      </div>
    </div>
  );
};
