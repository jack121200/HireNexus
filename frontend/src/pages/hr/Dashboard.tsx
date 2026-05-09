import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../../components/PageHeader";
import { StatCard } from "../../components/StatCard";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<DashboardResponse>("/api/hr/dashboard")
      .then(setData)
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return <div className="p-4 text-sm text-danger border border-danger/30 bg-danger/10 rounded-lg">{error}</div>;
  }

  return (
    <div className="space-y-8 page-enter">
      <PageHeader
        kicker="HR Intelligence"
        title="Command Center"
        subtitle="Monitor recruitment pipelines, AI screening performance, and candidate conversions."
        actions={(
          <Link to="/hr/post-job">
            <Button size="sm" className="shadow-glow">Post New Role</Button>
          </Link>
        )}
      />

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1,2,3,4,5,6].map(i => <div key={i} className="h-32 rounded-xl shimmer" />)}
        </div>
      ) : data ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <StatCard 
              tone="accent" 
              label="Active Roles" 
              value={data.jobs_posted} 
              icon="💼"
            />
            <StatCard 
              tone="cool" 
              label="Pipeline Volume" 
              value={data.applications_total} 
              icon="📄"
            />
            <StatCard 
              tone="accent" 
              label="AI Screens Completed" 
              value={data.interviews_completed} 
              icon="🤖"
            />
            <StatCard 
              tone="success" 
              label="Shortlisted" 
              value={data.shortlisted} 
              trend="up"
              icon="✓"
            />
            <StatCard 
              tone="danger" 
              label="Rejected" 
              value={data.rejected} 
              icon="✕"
            />
            <StatCard 
              tone="warning" 
              label="Action Required" 
              value={data.notifications_unread} 
              icon="🔔"
            />
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <Card variant="surface" className="h-64 flex items-center justify-center border-dashed">
              <div className="text-center space-y-2">
                <div className="text-2xl grayscale">📈</div>
                <div className="text-sm font-medium text-text">Pipeline Analytics</div>
                <div className="text-xs text-textDim">Conversion charts will appear here</div>
              </div>
            </Card>
            <Card variant="surface" className="h-64 flex items-center justify-center border-dashed">
              <div className="text-center space-y-2">
                <div className="text-2xl grayscale">⚡</div>
                <div className="text-sm font-medium text-text">AI Interview Insights</div>
                <div className="text-xs text-textDim">Aggregated confidence scores</div>
              </div>
            </Card>
          </div>
        </div>
      ) : null}
    </div>
  );
};
