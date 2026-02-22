import { type ReactNode } from "react";

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
    <div className="min-h-screen bg-ink text-text">
      <div className="min-h-screen neo-aurora-bg">
        <div className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center gap-12 px-6 py-16 md:flex-row">
          <div className="w-full max-w-md space-y-5">
            <div className="text-xs uppercase tracking-[0.35em] text-textMuted">HireNexus</div>
            <h1 className="font-display text-3xl font-semibold text-white md:text-4xl">{title}</h1>
            <p className="text-sm text-textMuted">{subtitle}</p>
            <div className="glass-panel rounded-2xl p-4 text-xs text-textMuted">
              Secure authentication powered by JWT with encrypted sessions and anomaly detection.
            </div>
            <div className="grid gap-3 text-sm text-textMuted">
              {["AI interview scoring", "Skill gap recommendations", "Live match confidence"].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-accent" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="w-full max-w-md">
            <div className="glass-panel rounded-3xl p-1">
              <div className="rounded-[22px] bg-panel/90 p-6">{children}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
