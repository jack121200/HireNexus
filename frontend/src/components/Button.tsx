import { type ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  glow?: boolean;
};

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-gradient-to-r from-accent via-accentSoft to-accentWarm text-white shadow-glow hover:brightness-110",
  secondary:
    "bg-panel/70 border border-border text-text hover:border-accent/70 hover:text-white",
  ghost: "bg-transparent text-text hover:bg-panelMuted/70",
  danger: "bg-gradient-to-r from-danger to-accentWarm text-white shadow-neon hover:brightness-110",
  outline: "border border-accent/60 text-text hover:border-accent hover:text-white",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2.5 text-sm",
  lg: "px-5 py-3 text-sm",
};

export const Button = ({
  variant = "primary",
  size = "md",
  glow = false,
  className = "",
  ...props
}: ButtonProps) => {
  return (
    <button
      className={`relative inline-flex items-center justify-center gap-2 rounded-full font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2 focus-visible:ring-offset-ink disabled:cursor-not-allowed disabled:opacity-60 ${variantStyles[variant]} ${sizeStyles[size]} ${
        glow ? "shadow-glow" : ""
      } ${className}`}
      {...props}
    />
  );
};
