import { type PropsWithChildren } from "react";

type BadgeProps = PropsWithChildren<{
  tone?: "default" | "success" | "warning" | "danger" | "info" | "brand";
  className?: string;
}>;

const tones: Record<NonNullable<BadgeProps["tone"]>, string> = {
  default: "bg-panelMuted/70 text-textMuted border-border/70",
  success: "bg-green-500/10 text-success border-green-500/30",
  warning: "bg-yellow-500/10 text-warning border-yellow-500/30",
  danger: "bg-red-500/10 text-danger border-red-500/30",
  info: "bg-blue-500/10 text-info border-blue-500/30",
  brand: "bg-accent/15 text-accent border-accent/40",
};

export const Badge = ({ tone = "default", className = "", children }: BadgeProps) => {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.15em] ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
};
