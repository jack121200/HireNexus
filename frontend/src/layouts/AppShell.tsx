import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { useAuth, type Role } from "../lib/auth";
import { apiFetch } from "../lib/api";

type MenuItem = {
  label: string;
  path: string;
};

const candidateMenu: MenuItem[] = [
  { label: "Dashboard", path: "/candidate/dashboard" },
  { label: "Resume", path: "/candidate/resume" },
  { label: "Jobs", path: "/candidate/jobs" },
  { label: "Mock Interview", path: "/candidate/mock-interview" },
  { label: "Notifications", path: "/candidate/notifications" },
  { label: "Chat", path: "/candidate/chat" },
];

const hrMenu: MenuItem[] = [
  { label: "Dashboard", path: "/hr/dashboard" },
  { label: "Post Job", path: "/hr/post-job" },
  { label: "Jobs & Applicants", path: "/hr/jobs" },
  { label: "Notifications", path: "/hr/notifications" },
  { label: "Chat", path: "/hr/chat" },
];

export const AppShell = ({ role }: { role: Role }) => {
  const { auth, logout } = useAuth();
  const menu = role === "candidate" ? candidateMenu : hrMenu;
  const location = useLocation();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const isInterviewRoute = location.pathname.includes("/interview/");

  useEffect(() => {
    const loadUnread = async () => {
      try {
        const path = role === "candidate" ? "/api/candidate/notifications/unread-count" : "/api/hr/notifications/unread-count";
        const data = await apiFetch<{ unread_count: number }>(path);
        setUnread(data.unread_count);
      } catch {
        setUnread(0);
      }
    };
    loadUnread();
  }, [role]);

  useEffect(() => {
    if (!auth.token) return;
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const wsUrl = baseUrl.replace("http", "ws");
    let socket: WebSocket | null = null;
    let retry = 0;
    let active = true;
    let reconnectTimer: number | null = null;

    const connect = () => {
      if (!active) return;
      socket = new WebSocket(`${wsUrl}/ws/notifications?token=${auth.token}`);
      socket.onopen = () => {
        retry = 0;
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === "notification.created") {
            setUnread((prev) => Math.max(prev + 1, payload.data?.unread_count ?? prev + 1));
          }
          if (payload.event === "notifications.unread_count") {
            setUnread(payload.data?.unread_count ?? 0);
          }
        } catch {
          // ignore
        }
      };
      socket.onclose = () => {
        if (!active) return;
        const delay = Math.min(1000 * 2 ** retry, 10000);
        retry += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      active = false;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [auth.token]);

  return (
    <div className="min-h-screen bg-ink text-text">
      <div className="min-h-screen neo-aurora-bg">
        <div className="flex min-h-screen">
          <aside className="relative w-72 border-r border-border/60 bg-panel/60 px-6 py-8 backdrop-blur">
            <div className="space-y-2">
              <div className="font-display text-2xl font-semibold text-white">
                Hire<span className="text-gradient">Nexus</span>
              </div>
              <div className="text-xs uppercase tracking-[0.3em] text-textMuted">{role} workspace</div>
            </div>
            <nav className="mt-10 flex flex-col gap-2">
              {menu.map((item) => {
                const basePath = item.path.split("/").slice(0, 3).join("/");
                const matchesApplicants =
                  item.path === "/hr/jobs" && location.pathname.startsWith("/hr/job/");
                const active = location.pathname.startsWith(basePath) || matchesApplicants;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`relative rounded-xl border px-4 py-3 text-sm transition ${
                      active
                        ? "border-accent/50 bg-panelMuted/80 text-white shadow-glow before:absolute before:left-2 before:top-2 before:bottom-2 before:w-1 before:rounded-full before:bg-gradient-to-b before:from-accent before:to-accentWarm"
                        : "border-transparent text-textMuted hover:border-border/70 hover:bg-panelMuted/60 hover:text-white"
                    }`}
                  >
                    {item.label}
                  </NavLink>
                );
              })}
            </nav>
          </aside>

          <main className="flex-1">
            <header className="flex items-center justify-between border-b border-border/70 bg-panel/60 px-6 py-5 backdrop-blur">
              <div>
                <div className="text-xs uppercase tracking-[0.3em] text-textMuted">Welcome back</div>
                <div className="text-lg font-semibold text-white">{auth.user?.full_name}</div>
              </div>
              <div className="flex items-center gap-4">
                <div className="rounded-full border border-border/70 bg-panelMuted/60 px-3 py-1 text-xs text-textMuted">
                  Unread: {unread}
                </div>
                <Button
                  variant="ghost"
                  onClick={() => {
                    logout();
                    navigate("/");
                  }}
                >
                  Sign out
                </Button>
              </div>
            </header>
            <div className="px-6 py-8">
              <div className={`mx-auto w-full ${isInterviewRoute ? "max-w-[1400px]" : "max-w-6xl"}`}>
                <Outlet />
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};
