import { type PropsWithChildren } from "react";

type Variant = "surface" | "glass" | "outline" | "muted";
type Padding = "sm" | "md" | "lg";

type CardProps = PropsWithChildren<{
  className?: string;
  variant?: Variant;
  interactive?: boolean;
  padding?: Padding;
}>;

const variantStyles: Record<Variant, string> = {
  surface: "bg-panel border-border",
  glass: "glass-panel",
  outline: "bg-transparent border-border",
  muted: "bg-panelMuted border-border",
};

const paddingStyles: Record<Padding, string> = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export const Card = ({
  className = "",
  variant = "surface",
  interactive = false,
  padding = "md",
  children,
}: CardProps) => {
  return (
    <div
      className={`rounded-xl border shadow-card ${variantStyles[variant]} ${paddingStyles[padding]} ${
        interactive ? "card-interactive cursor-pointer" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
};
