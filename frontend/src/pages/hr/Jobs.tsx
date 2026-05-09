import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch } from "../../lib/api";

type Job = {
  id: number;
  title: string;
  location?: string | null;
  employment_type?: string | null;
  created_at: string;
};

type JobBrowseResponse = { items: Job[]; };

export const HrJobs = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<JobBrowseResponse>("/api/hr/jobs")
      .then((data) => setJobs(data.items))
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 page-enter pb-20">
      <PageHeader
        kicker="HR Suite"
        title="Active Postings"
        subtitle="Manage your roles and review AI-screened applicants."
        actions={
          <Link to="/hr/post-job">
            <Button size="sm">Post New Role</Button>
          </Link>
        }
      />
      
      {error && <div className="p-3 text-sm text-danger border border-danger/30 bg-danger/10 rounded-lg">{error}</div>}

      {loading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-24 rounded-xl shimmer" />)}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState title="No active roles" description="Post a job to start sourcing candidates through our AI pipeline." />
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <Card key={job.id} variant="surface" className="card-interactive flex flex-col sm:flex-row sm:items-center justify-between gap-4 group">
              <div>
                <Link to={`/hr/job/${job.id}/applicants`} className="block">
                  <h3 className="text-lg font-bold text-text group-hover:text-accent transition-colors mb-1">{job.title}</h3>
                </Link>
                <div className="text-sm font-medium text-textMuted flex items-center gap-2">
                  <span className="flex items-center gap-1">📍 {job.location || "Remote"}</span>
                  <span className="text-border">|</span>
                  <span className="flex items-center gap-1">💼 {job.employment_type || "Full-time"}</span>
                  <span className="text-border hidden sm:inline">|</span>
                  <span className="text-[11px] text-textDim hidden sm:inline uppercase">Posted {new Date(job.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              
              <div className="flex shrink-0 items-center justify-end">
                <Link to={`/hr/job/${job.id}/applicants`}>
                  <Button variant="secondary" size="sm" className="group-hover:bg-accent group-hover:text-white transition-colors border-border group-hover:border-accent">
                    Manage Pipeline <span className="ml-1 opacity-50">&rarr;</span>
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
