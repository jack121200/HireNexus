type EmptyStateProps = {
  title: string;
  description: string;
};

export const EmptyState = ({ title, description }: EmptyStateProps) => {
  return (
    <div className="rounded-2xl border border-dashed border-border/70 bg-panel/40 p-8 text-center">
      <div className="text-base font-semibold text-white">{title}</div>
      <p className="mt-2 text-sm text-textMuted">{description}</p>
    </div>
  );
};
