import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { useAuth, type Role } from "../lib/auth";
import { apiFetch } from "../lib/api";

/* ════════════════════════════════════════════════════════════════════════════
   APP SHELL — Midnight Prism sidebar + top bar
   ════════════════════════════════════════════════════════════════════════════ */

type MenuItem = { label: string; icon: string; path: string };

const candidateMenu: MenuItem[] = [
  { label: "Dashboard",      icon: "📊",  path: "/candidate/dashboard" },
  { label: "Resume",         icon: "📄",  path: "/candidate/resume" },
  { label: "Jobs",           icon: "💼",  path: "/candidate/jobs" },
  { label: "Interviews",     icon: "🎙️", path: "/candidate/interviews" },
  { label: "Mock Interview", icon: "🧑‍💻", path: "/candidate/mock-interview" },
  { label: "Career Guide",   icon: "🧠",  path: "/candidate/career-guide" },
  { label: "Notifications",  icon: "🔔",  path: "/candidate/notifications" },
  { label: "Chat",           icon: "💬",  path: "/candidate/chat" },
];

const hrMenu: MenuItem[] = [
  { label: "Dashboard", icon: "📊", path: "/hr/dashboard" },
  { label: "Post Job", icon: "➕", path: "/hr/post-job" },
  { label: "Jobs & Applicants", icon: "📋", path: "/hr/jobs" },
  { label: "Notifications", icon: "🔔", path: "/hr/notifications" },
  { label: "Chat", icon: "💬", path: "/hr/chat" },
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
      socket.onopen = () => { retry = 0; };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === "notification.created") {
            setUnread((prev) => Math.max(prev + 1, payload.data?.unread_count ?? prev + 1));
          }
          if (payload.event === "notifications.unread_count") {
            setUnread(payload.data?.unread_count ?? 0);
          }
        } catch { /* ignore */ }
      };
      socket.onclose = () => {
        if (!active) return;
        const delay = Math.min(1000 * 2 ** retry, 10000);
        retry += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => { socket?.close(); };
    };

    connect();
    return () => {
      active = false;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (socket) {
        if (socket.readyState === WebSocket.CONNECTING) {
          socket.onopen = () => socket?.close();
        } else {
          socket.close();
        }
      }
    };
  }, [auth.token]);

  return (
    <div className="min-h-screen bg-ink text-text">
      <div className="flex min-h-screen">

        {/* ── Sidebar ──────────────────────────────────────────────────── */}
        <aside className="fixed inset-y-0 left-0 z-30 w-56 border-r border-border bg-panel flex flex-col">
          {/* Brand */}
          <div className="px-5 pt-6 pb-4">
            <div className="font-display text-lg font-bold text-text tracking-tight">
              Hire<span className="text-accent">Nexus</span>
            </div>
            <div className="text-[10px] text-textDim mt-0.5 capitalize">{role} workspace</div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
            {menu.map((item) => {
              const basePath = item.path.split("/").slice(0, 3).join("/");
              const matchesApplicants = item.path === "/hr/jobs" && location.pathname.startsWith("/hr/job/");
              const isActive = location.pathname.startsWith(basePath) || matchesApplicants;
              const isNotif = item.label === "Notifications";
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-all duration-150 ${
                    isActive
                      ? "bg-accent/10 text-accent font-medium"
                      : "text-textMuted hover:bg-panelMuted hover:text-text"
                  }`}
                >
                  <span className="text-sm">{item.icon}</span>
                  <span className="flex-1">{item.label}</span>
                  {isNotif && unread > 0 && (
                    <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-accent text-[10px] font-bold text-white px-1">
                      {unread}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>

          {/* User footer */}
          <div className="border-t border-border px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10 border border-accent/20 text-xs font-bold text-accent">
                {auth.user?.full_name?.charAt(0)?.toUpperCase() ?? "U"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-text truncate">{auth.user?.full_name}</div>
                <div className="text-[11px] text-textDim truncate">{auth.user?.email}</div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full mt-3 !text-textMuted"
              onClick={() => { logout(); navigate("/"); }}
            >
              Sign out
            </Button>
          </div>
        </aside>

        {/* ── Main content ──────────────────────────────────────────────── */}
        <main className="flex-1 ml-56 min-h-screen">
          {/* Top bar */}
          <header className="sticky top-0 z-20 border-b border-border bg-ink/80 backdrop-blur-lg px-6 py-3.5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-text">
                Welcome back, {auth.user?.full_name?.split(" ")[0]}
              </div>
              <div className="flex items-center gap-3">
                {unread > 0 && (
                  <NavLink
                    to={`/${role}/notifications`}
                    className="flex items-center gap-1.5 rounded-lg border border-border bg-panelMuted px-3 py-1.5 text-xs text-textMuted hover:border-borderHover transition-colors"
                  >
                    🔔 <span className="text-accent font-medium">{unread}</span> unread
                  </NavLink>
                )}
              </div>
            </div>
          </header>

          {/* Page content */}
          <div className="px-6 py-6">
            <div className={`mx-auto w-full ${isInterviewRoute ? "max-w-[1400px]" : "max-w-5xl"}`}>
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
