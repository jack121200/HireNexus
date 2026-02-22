import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../../components/PageHeader";
import { StatCard } from "../../components/StatCard";
import { Button } from "../../components/Button";
import { apiFetch } from "../../lib/api";

type DashboardResponse = {
  jobs_posted: number;
  applications_total: number;
  shortlisted: number;
  rejected: number;
  interviews_completed: number;
  notifications_unread: number;
};

export const HrDashboard = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DashboardResponse>("/api/hr/dashboard")
      .then(setData)
      .catch((err) => setError((err as Error).message));
  }, []);

  if (error) {
    return <div className="text-danger">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="HR Suite"
        title="HR Dashboard"
        subtitle="Monitor job performance, applicant status, and interview activity."
        actions={(
          <Link to="/hr/post-job">
            <Button size="sm">Post a Job</Button>
          </Link>
        )}
      />
      {!data && <div className="text-textMuted">Loading...</div>}
      {data && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatCard tone="accent" label="Jobs Posted" value={data.jobs_posted} />
          <StatCard tone="cool" label="Applications" value={data.applications_total} />
          <StatCard tone="warm" label="Shortlisted" value={data.shortlisted} />
          <StatCard tone="warm" label="Rejected" value={data.rejected} />
          <StatCard tone="accent" label="Interviews Completed" value={data.interviews_completed} />
          <StatCard tone="cool" label="Unread Notifications" value={data.notifications_unread} />
        </div>
      )}
    </div>
  );
};
