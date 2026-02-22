import { type PropsWithChildren } from "react";

type Variant = "surface" | "glass" | "outline" | "muted";
type Padding = "sm" | "md" | "lg";

type CardProps = PropsWithChildren<{
  className?: string;
  variant?: Variant;
  glow?: boolean;
  padding?: Padding;
}>;

const variantStyles: Record<Variant, string> = {
  surface: "bg-panel/85 border-border",
  glass: "glass-panel border-accent/20",
  outline: "bg-transparent border-border/80",
  muted: "bg-panelMuted/80 border-border/70",
};

const paddingStyles: Record<Padding, string> = {
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
};

export const Card = ({
  className = "",
  variant = "surface",
  glow = false,
  padding = "md",
  children,
}: CardProps) => {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border ${variantStyles[variant]} ${paddingStyles[padding]} ${
        glow ? "shadow-glow" : "shadow-[0_20px_60px_rgba(0,0,0,0.35)]"
      } ${className}`}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-accentWarm/10" />
      <div className="relative z-10">{children}</div>
    </div>
  );
};
