import { type ReactNode } from "react";
import { Link } from "react-router-dom";

export const AuthLayout = ({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) => {
  return (
    <div className="min-h-screen bg-ink text-text page-enter">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-accent/5 rounded-full blur-[100px]" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-12 px-6 py-16 md:flex-row">
        {/* LEFT: Brand + info */}
        <div className="w-full max-w-md space-y-6">
          <Link to="/" className="font-display text-xl font-bold text-text tracking-tight">
            Hire<span className="text-accent">Nexus</span>
          </Link>

          <h1 className="text-3xl font-bold text-text tracking-tight">{title}</h1>
          <p className="text-sm text-textMuted leading-relaxed">{subtitle}</p>

          <div className="space-y-3 pt-4">
            {["AI-powered voice interviews", "Intelligent scoring engine", "Real-time career guidance"].map((item) => (
              <div key={item} className="flex items-center gap-3 text-sm text-textMuted">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10 border border-accent/20">
                  <span className="text-accent text-[10px]">✓</span>
                </div>
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT: Form card */}
        <div className="w-full max-w-md">
          <div className="rounded-xl border border-border bg-panel p-6 shadow-card">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};
