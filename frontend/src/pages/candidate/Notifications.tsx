import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { Input } from "../../components/Input";
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

export const CandidateNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = () => {
    apiFetch<NotificationsResponse>("/api/candidate/notifications")
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
      const data = await apiFetch<{ unread_count: number }>(`/api/candidate/notifications/${id}/read`, {
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
      const data = await apiFetch<{ unread_count: number }>(`/api/candidate/notifications/mark-all-read`, {
        method: "POST",
      });
      setUnread(data.unread_count);
      loadNotifications();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const filtered = useMemo(() => {
    if (!search) return notifications;
    const lower = search.toLowerCase();
    return notifications.filter(
      (item) => item.title.toLowerCase().includes(lower) || item.body.toLowerCase().includes(lower)
    );
  }, [notifications, search]);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Candidate Suite"
        title="Notifications"
        subtitle="Stay updated on interviews, applications, and HR messages."
        actions={
          <Button variant="secondary" onClick={markAll}>
            Mark all read ({unread})
          </Button>
        }
      />
      {error && <p className="text-danger">{error}</p>}
      <Card variant="glass" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <Input
          label="Search notifications"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="flex items-center gap-3 text-xs text-textMuted">
          <span>Total: {notifications.length}</span>
          <span>Unread: {unread}</span>
        </div>
      </Card>

      {filtered.length === 0 && (
        <EmptyState title="No notifications" description="Updates will appear here as they arrive." />
      )}
      <div className="space-y-3">
        {filtered.map((notification) => (
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
            <div className="flex items-center justify-between text-xs text-textMuted">
              <span>{new Date(notification.created_at).toLocaleString()}</span>
              {!notification.is_read && <span className="text-accent">New</span>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
