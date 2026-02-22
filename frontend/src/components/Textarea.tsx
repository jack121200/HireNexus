import { type TextareaHTMLAttributes } from "react";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
};

export const Textarea = ({ label, className = "", ...props }: TextareaProps) => {
  return (
    <label className="flex w-full flex-col gap-2 text-sm text-textMuted">
      {label && <span className="text-xs uppercase tracking-[0.2em] text-textMuted">{label}</span>}
      <textarea
        className={`min-h-[120px] w-full rounded-xl border border-border/70 bg-panel/70 px-4 py-3 text-sm text-text outline-none transition placeholder:text-textMuted/70 focus:border-accent focus:ring-2 focus:ring-accent/30 ${className}`}
        {...props}
      />
    </label>
  );
};
