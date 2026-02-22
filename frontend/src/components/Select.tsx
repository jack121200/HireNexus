import { type SelectHTMLAttributes } from "react";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
};

export const Select = ({ label, className = "", children, ...props }: SelectProps) => {
  return (
    <label className="flex w-full flex-col gap-2 text-sm text-textMuted">
      {label && <span className="text-xs uppercase tracking-[0.2em] text-textMuted">{label}</span>}
      <select
        className={`w-full rounded-xl border border-border/70 bg-panel/70 px-4 py-2.5 text-sm text-text outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/30 ${className}`}
        {...props}
      >
        {children}
      </select>
    </label>
  );
};
