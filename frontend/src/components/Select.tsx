import { type SelectHTMLAttributes } from "react";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
};

export const Select = ({ label, className = "", children, ...props }: SelectProps) => {
  return (
    <label className="flex w-full flex-col gap-1.5 text-sm">
      {label && <span className="text-xs font-medium text-textMuted">{label}</span>}
      <select
        className={`w-full rounded-lg border border-border bg-panelMuted px-3.5 py-2.5 text-sm text-text outline-none transition-all duration-150 focus:border-accent focus:ring-2 focus:ring-accent/20 ${className}`}
        {...props}
      >
        {children}
      </select>
    </label>
  );
};
