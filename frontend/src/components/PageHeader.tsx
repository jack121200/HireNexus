import { type ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  kicker?: string;
};

export const PageHeader = ({ title, subtitle, actions, kicker = "HireNexus" }: PageHeaderProps) => {
  return (
    <div className="flex flex-col gap-4 border-b border-border/70 pb-6 md:flex-row md:items-center md:justify-between">
      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.4em] text-textMuted">{kicker}</div>
        <h1 className="font-display text-3xl font-semibold text-white md:text-4xl">{title}</h1>
        {subtitle && <p className="max-w-2xl text-sm text-textMuted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
};
