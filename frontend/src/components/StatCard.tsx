import { type ReactNode } from "react";

type StatCardProps = {
  label: string;
  value: ReactNode;
  description?: string;
  icon?: string;
  trend?: "up" | "down" | "neutral";
};

export const StatCard = ({ label, value, description, icon, trend }: StatCardProps) => {
  return (
    <div className="rounded-xl border border-border bg-panel p-5 shadow-card card-interactive">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-medium text-textMuted">{label}</div>
          <div className="mt-2 text-2xl font-semibold text-text tracking-tight">{value}</div>
        </div>
        {icon && (
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-panelMuted border border-border text-lg">
            {icon}
          </span>
        )}
      </div>
      {description && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-textMuted">
          {trend === "up" && <span className="text-success">↑</span>}
          {trend === "down" && <span className="text-danger">↓</span>}
          {description}
        </div>
      )}
    </div>
  );
};
