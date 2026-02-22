import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../../components/PageHeader";
import { StatCard } from "../../components/StatCard";
import { Card } from "../../components/Card";
import { apiFetch } from "../../lib/api";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";

type DashboardResponse = {
  resume_score: number;
  jobs_applied: number;
  jobs_shortlisted: number;
  interview_performance: {
    ai_average: number;
    mock_average: number;
    total_completed: number;
  };
  notifications_unread: number;
};

type Resume = {
  id: number;
  file_name: string;
  is_primary: boolean;
  extracted_skills: string[];
  estimated_experience_years: number | null;
  education_level: string | null;
};

type InterviewItem = {
  id: number;
  type: "ai" | "mock";
  status: string;
  overall_score: number | null;
  created_at: string;
};

type Notification = {
  id: number;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
};

type JobItem = {
  id: number;
  title: string;
  location?: string | null;
  employment_type?: string | null;
  required_skills: string[];
  eligibility: {
    eligibility_percentage: number;
    missing_skills: string[];
  } | null;
};

type JobBrowseResponse = {
  items: JobItem[];
};

type NotificationsResponse = {
  items: Notification[];
};

export const CandidateDashboard = () => {
  const [summary, setSummary] = useState<DashboardResponse | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [interviews, setInterviews] = useState<InterviewItem[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryRes, resumeRes, interviewRes, notifRes] = await Promise.all([
          apiFetch<DashboardResponse>("/api/candidate/dashboard"),
          apiFetch<Resume[]>("/api/candidate/resumes"),
          apiFetch<{ items: InterviewItem[] }>("/api/candidate/interviews"),
          apiFetch<NotificationsResponse>("/api/candidate/notifications"),
        ]);
        setSummary(summaryRes);
        setResumes(resumeRes);
        setInterviews(interviewRes.items);
        setNotifications(notifRes.items);

        const primary = resumeRes.find((resume) => resume.is_primary) ?? resumeRes[0];
        if (primary) {
          const jobRes = await apiFetch<JobBrowseResponse>(`/api/candidate/jobs?resume_id=${primary.id}`);
          setJobs(jobRes.items);
        }
      } catch (err) {
        setError((err as Error).message);
      }
    };

    load();
  }, []);

  const primaryResume = resumes.find((resume) => resume.is_primary) ?? resumes[0];

  const topMatches = useMemo(() => {
    return [...jobs]
      .filter((job) => job.eligibility)
      .sort((a, b) => (b.eligibility?.eligibility_percentage ?? 0) - (a.eligibility?.eligibility_percentage ?? 0))
      .slice(0, 3);
  }, [jobs]);

  const interviewStats = useMemo(() => {
    const ai = interviews.filter((item) => item.type === "ai");
    const mock = interviews.filter((item) => item.type === "mock");
    return {
      aiCount: ai.length,
      mockCount: mock.length,
      recent: interviews.slice(0, 3),
    };
  }, [interviews]);

  if (error) {
    return <div className="text-danger">{error}</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Candidate Suite"
        title="Candidate Command Center"
        subtitle="Your full career snapshot: resume strength, job matches, interviews, and activity in one place."
        actions={(
          <>
            <Link to="/candidate/mock-interview">
              <Button variant="secondary" size="sm">
                Start Mock Interview
              </Button>
            </Link>
            <Link to="/candidate/jobs">
              <Button size="sm">Browse Jobs</Button>
            </Link>
          </>
        )}
      />

      {!summary && <div className="text-textMuted">Loading dashboard...</div>}

      {summary && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard tone="accent" label="Resume Score" value={`${summary.resume_score.toFixed(1)}%`} description="Latest eligibility strength" />
          <StatCard tone="cool" label="Jobs Applied" value={summary.jobs_applied} description="Active applications" />
          <StatCard tone="warm" label="Shortlisted" value={summary.jobs_shortlisted} description="Shortlisted by HR" />
          <StatCard
            tone="accent"
            label="Interview Performance"
            value={`${summary.interview_performance.total_completed}`}
            description={`AI Avg ${summary.interview_performance.ai_average.toFixed(1)} - Mock Avg ${summary.interview_performance.mock_average.toFixed(1)}`}
          />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card variant="glass" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm uppercase tracking-wide text-textMuted">Profile Status</div>
              <div className="text-lg font-semibold text-white">Candidate Snapshot</div>
            </div>
            <Badge tone={primaryResume ? "success" : "warning"}>
              {primaryResume ? "Resume Ready" : "Resume Missing"}
            </Badge>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-border bg-panelMuted p-3 text-sm">
              <div className="text-xs uppercase text-textMuted">Primary Resume</div>
              <div className="mt-2 font-semibold text-white">{primaryResume?.file_name ?? "Upload a resume"}</div>
            </div>
            <div className="rounded-lg border border-border bg-panelMuted p-3 text-sm">
              <div className="text-xs uppercase text-textMuted">Experience</div>
              <div className="mt-2 font-semibold text-white">
                {primaryResume?.estimated_experience_years ?? "N/A"} yrs
              </div>
            </div>
            <div className="rounded-lg border border-border bg-panelMuted p-3 text-sm">
              <div className="text-xs uppercase text-textMuted">Education</div>
              <div className="mt-2 font-semibold text-white">{primaryResume?.education_level ?? "N/A"}</div>
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-textMuted">Top Skills</div>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {(primaryResume?.extracted_skills ?? []).slice(0, 10).map((skill) => (
                <span key={skill} className="rounded-full border border-border px-2 py-1 text-textMuted">
                  {skill}
                </span>
              ))}
              {!primaryResume?.extracted_skills?.length && (
                <span className="text-textMuted">No skills extracted yet</span>
              )}
            </div>
          </div>
        </Card>

        <Card variant="glass" className="space-y-4">
          <div className="text-sm uppercase tracking-wide text-textMuted">Interview Momentum</div>
          <div className="text-lg font-semibold text-white">Your Practice and AI Sessions</div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-border bg-panelMuted p-3 text-sm">
              <div className="text-xs uppercase text-textMuted">AI Interviews</div>
              <div className="mt-2 text-2xl font-semibold text-white">{interviewStats.aiCount}</div>
            </div>
            <div className="rounded-lg border border-border bg-panelMuted p-3 text-sm">
              <div className="text-xs uppercase text-textMuted">Mock Interviews</div>
              <div className="mt-2 text-2xl font-semibold text-white">{interviewStats.mockCount}</div>
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-textMuted">Recent Sessions</div>
            <div className="mt-2 space-y-2 text-sm">
              {interviewStats.recent.length === 0 && <div className="text-textMuted">No interviews yet.</div>}
              {interviewStats.recent.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-md border border-border bg-panelMuted px-3 py-2">
                  <div>
                    <div className="font-semibold text-white">{item.type.toUpperCase()} Interview</div>
                    <div className="text-xs text-textMuted">{new Date(item.created_at).toLocaleString()}</div>
                  </div>
                  <div className="text-xs text-textMuted">Score: {item.overall_score?.toFixed(1) ?? "Pending"}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card variant="glass" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm uppercase tracking-wide text-textMuted">Job Matches</div>
              <div className="text-lg font-semibold text-white">Top Roles For You</div>
            </div>
            <Badge tone="info">Live eligibility</Badge>
          </div>
          <div className="space-y-3">
            {topMatches.length === 0 && <div className="text-textMuted">Add a resume to unlock matches.</div>}
            {topMatches.map((job) => (
              <div key={job.id} className="rounded-lg border border-border bg-panelMuted p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-white">{job.title}</div>
                    <div className="text-xs text-textMuted">
                      {job.location || "Remote"} - {job.employment_type || "Full-time"}
                    </div>
                  </div>
                  <div className="text-sm text-white">
                    {job.eligibility?.eligibility_percentage.toFixed(1)}%
                  </div>
                </div>
                <div className="mt-2 text-xs text-textMuted">
                  Missing skills: {job.eligibility?.missing_skills.slice(0, 3).join(", ") || "None"}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card variant="glass" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm uppercase tracking-wide text-textMuted">Notifications</div>
              <div className="text-lg font-semibold text-white">Recent Updates</div>
            </div>
            {summary && <Badge tone="warning">Unread {summary.notifications_unread}</Badge>}
          </div>
          <div className="space-y-3">
            {notifications.slice(0, 5).map((notif) => (
              <div key={notif.id} className="rounded-lg border border-border bg-panelMuted p-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-white">{notif.title}</div>
                  {!notif.is_read && <span className="text-xs text-accent">New</span>}
                </div>
                <div className="mt-1 text-xs text-textMuted">{notif.body}</div>
                <div className="mt-2 text-[11px] text-textMuted">{new Date(notif.created_at).toLocaleString()}</div>
              </div>
            ))}
            {notifications.length === 0 && <div className="text-textMuted">No notifications yet.</div>}
          </div>
        </Card>
      </div>
    </div>
  );
};
