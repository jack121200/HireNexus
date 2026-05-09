import { type InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

export const Input = ({ label, className = "", ...props }: InputProps) => {
  return (
    <label className="flex w-full flex-col gap-1.5 text-sm">
      {label && (
        <span className="text-xs font-medium text-textMuted">{label}</span>
      )}
      <input
        className={`w-full rounded-lg border border-border bg-panelMuted px-3.5 py-2.5 text-sm text-text outline-none transition-all duration-150 placeholder:text-textDim focus:border-accent focus:ring-2 focus:ring-accent/20 ${className}`}
        {...props}
      />
    </label>
  );
};
