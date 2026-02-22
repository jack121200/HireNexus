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

type JobBrowseResponse = {
  items: Job[];
};

export const HrJobs = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<JobBrowseResponse>("/api/hr/jobs")
      .then((data) => setJobs(data.items))
      .catch((err) => setError((err as Error).message));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="HR Suite"
        title="Jobs & Applicants"
        subtitle="Manage your postings and review applicants with AI insights."
      />
      {error && <p className="text-danger">{error}</p>}
      {jobs.length === 0 && (
        <EmptyState title="No jobs yet" description="Post your first role to start receiving applicants." />
      )}
      <div className="grid gap-4">
        {jobs.map((job) => (
          <Card key={job.id} variant="glass" className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-white">{job.title}</div>
              <div className="text-xs text-textMuted">
                {job.location || "Remote"} - {job.employment_type || "Full-time"}
              </div>
            </div>
            <Link to={`/hr/job/${job.id}/applicants`}>
              <Button variant="secondary">View Applicants</Button>
            </Link>
          </Card>
        ))}
      </div>
    </div>
  );
};
