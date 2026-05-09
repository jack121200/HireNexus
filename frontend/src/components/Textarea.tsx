import { type TextareaHTMLAttributes } from "react";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
};

export const Textarea = ({ label, className = "", ...props }: TextareaProps) => {
  return (
    <label className="flex w-full flex-col gap-1.5 text-sm">
      {label && <span className="text-xs font-medium text-textMuted">{label}</span>}
      <textarea
        className={`min-h-[120px] w-full rounded-lg border border-border bg-panelMuted px-3.5 py-3 text-sm text-text outline-none transition-all duration-150 placeholder:text-textDim focus:border-accent focus:ring-2 focus:ring-accent/20 resize-y ${className}`}
        {...props}
      />
    </label>
  );
};
