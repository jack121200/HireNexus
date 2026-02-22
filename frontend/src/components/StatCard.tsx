import { type ReactNode } from "react";

type StatCardProps = {
  label: string;
  value: ReactNode;
  description?: string;
  tone?: "default" | "accent" | "cool" | "warm";
};

const toneStyles: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "from-white/5 via-transparent to-white/5",
  accent: "from-accent/20 via-transparent to-accentWarm/15",
  cool: "from-accentCool/20 via-transparent to-accent/10",
  warm: "from-accentWarm/25 via-transparent to-accentSoft/10",
};

export const StatCard = ({ label, value, description, tone = "default" }: StatCardProps) => {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-panel/80 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${toneStyles[tone]}`} />
      <div className="relative z-10">
        <div className="text-xs uppercase tracking-[0.2em] text-textMuted">{label}</div>
        <div className="mt-3 text-2xl font-semibold text-white">{value}</div>
        {description && <div className="mt-2 text-xs text-textMuted">{description}</div>}
      </div>
    </div>
  );
};
