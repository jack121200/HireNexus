import { type ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  kicker?: string;
};

export const PageHeader = ({ title, subtitle, actions, kicker }: PageHeaderProps) => {
  return (
    <div className="flex flex-col gap-4 pb-6 md:flex-row md:items-end md:justify-between">
      <div className="space-y-1">
        {kicker && <div className="text-xs font-medium text-textMuted">{kicker}</div>}
        <h1 className="font-display text-2xl font-bold text-text tracking-tight md:text-3xl">{title}</h1>
        {subtitle && <p className="max-w-xl text-sm text-textMuted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
};
