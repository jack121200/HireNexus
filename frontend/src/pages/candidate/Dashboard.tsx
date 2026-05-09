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

  const primaryResume = resumes.find((r) => r.is_primary) ?? resumes[0];

  const topMatches = useMemo(() => {
    return [...jobs]
      .filter((j) => j.eligibility)
      .sort((a, b) => (b.eligibility?.eligibility_percentage ?? 0) - (a.eligibility?.eligibility_percentage ?? 0))
      .slice(0, 3);
  }, [jobs]);

  const interviewStats = useMemo(() => {
    const ai = interviews.filter((i) => i.type === "ai");
    const mock = interviews.filter((i) => i.type === "mock");
    return { aiCount: ai.length, mockCount: mock.length, recent: interviews.slice(0, 3) };
  }, [interviews]);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <div className="text-danger text-sm">⚠ {error}</div>
          <button onClick={() => window.location.reload()} className="text-xs text-accent hover:underline">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter">
      <PageHeader
        title="Dashboard"
        subtitle="Your career snapshot — resume strength, job matches, and interview performance."
        actions={
          <>
            <Link to="/candidate/mock-interview">
              <Button variant="secondary" size="sm">Mock Interview</Button>
            </Link>
            <Link to="/candidate/jobs">
              <Button size="sm">Browse Jobs</Button>
            </Link>
          </>
        }
      />

      {/* Loading skeleton */}
      {!summary && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 rounded-xl shimmer" />
          ))}
        </div>
      )}

      {/* Stats */}
      {summary && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard icon="📄" label="Resume Score" value={`${summary.resume_score.toFixed(1)}%`} description="Latest eligibility strength" />
          <StatCard icon="📬" label="Jobs Applied" value={summary.jobs_applied} description="Active applications" trend="up" />
          <StatCard icon="⭐" label="Shortlisted" value={summary.jobs_shortlisted} description="Selected by HR" />
          <StatCard
            icon="🎯"
            label="Interviews"
            value={summary.interview_performance.total_completed}
            description={`AI Avg ${summary.interview_performance.ai_average.toFixed(1)} · Mock Avg ${summary.interview_performance.mock_average.toFixed(1)}`}
          />
        </div>
      )}

      {/* Profile + Interview momentum */}
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        {/* Profile Card */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">Profile Snapshot</h2>
            <Badge tone={primaryResume ? "success" : "warning"}>
              {primaryResume ? "Resume Ready" : "Upload Resume"}
            </Badge>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 mb-4">
            <div className="rounded-lg bg-panelMuted border border-border p-3">
              <div className="text-xs text-textMuted">Primary Resume</div>
              <div className="mt-1 text-sm font-medium text-text truncate">{primaryResume?.file_name ?? "—"}</div>
            </div>
            <div className="rounded-lg bg-panelMuted border border-border p-3">
              <div className="text-xs text-textMuted">Experience</div>
              <div className="mt-1 text-sm font-medium text-text">{primaryResume?.estimated_experience_years ?? "—"} yrs</div>
            </div>
            <div className="rounded-lg bg-panelMuted border border-border p-3">
              <div className="text-xs text-textMuted">Education</div>
              <div className="mt-1 text-sm font-medium text-text">{primaryResume?.education_level ?? "—"}</div>
            </div>
          </div>

          <div>
            <div className="text-xs text-textMuted mb-2">Top Skills</div>
            <div className="flex flex-wrap gap-1.5">
              {(primaryResume?.extracted_skills ?? []).slice(0, 10).map((skill) => (
                <span key={skill} className="rounded-md bg-panelMuted border border-border px-2 py-0.5 text-xs text-textMuted">
                  {skill}
                </span>
              ))}
              {!primaryResume?.extracted_skills?.length && (
                <span className="text-xs text-textDim">No skills extracted yet</span>
              )}
            </div>
          </div>
        </Card>

        {/* Interview Momentum */}
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4">Interview Momentum</h2>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="rounded-lg bg-panelMuted border border-border p-3 text-center">
              <div className="text-2xl font-bold text-text">{interviewStats.aiCount}</div>
              <div className="text-xs text-textMuted mt-1">AI Interviews</div>
            </div>
            <div className="rounded-lg bg-panelMuted border border-border p-3 text-center">
              <div className="text-2xl font-bold text-text">{interviewStats.mockCount}</div>
              <div className="text-xs text-textMuted mt-1">Mock Sessions</div>
            </div>
          </div>

          <div>
            <div className="text-xs text-textMuted mb-2">Recent Sessions</div>
            <div className="space-y-2">
              {interviewStats.recent.length === 0 && <div className="text-xs text-textDim">No interviews yet.</div>}
              {interviewStats.recent.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-lg bg-panelMuted border border-border px-3 py-2">
                  <div>
                    <div className="text-sm font-medium text-text">{item.type === "ai" ? "AI" : "Mock"} Interview</div>
                    <div className="text-xs text-textDim">{new Date(item.created_at).toLocaleDateString()}</div>
                  </div>
                  <div className="text-sm font-medium text-accent">{item.overall_score?.toFixed(1) ?? "—"}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Job matches + Notifications */}
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        {/* Job matches */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">Top Job Matches</h2>
            <Badge tone="info">Live Eligibility</Badge>
          </div>
          <div className="space-y-2">
            {topMatches.length === 0 && <div className="text-xs text-textDim">Add a resume to unlock matches.</div>}
            {topMatches.map((job) => (
              <Link key={job.id} to={`/candidate/jobs/${job.id}`} className="block rounded-lg bg-panelMuted border border-border p-3 card-interactive">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-text">{job.title}</div>
                    <div className="text-xs text-textDim">{job.location || "Remote"} · {job.employment_type || "Full-time"}</div>
                  </div>
                  <div className="text-sm font-semibold text-success">{job.eligibility?.eligibility_percentage.toFixed(0)}%</div>
                </div>
                {(job.eligibility?.missing_skills?.length ?? 0) > 0 && (
                  <div className="mt-2 text-xs text-textDim">
                    Missing: {job.eligibility?.missing_skills.slice(0, 3).join(", ")}
                  </div>
                )}
              </Link>
            ))}
          </div>
        </Card>

        {/* Notifications */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text">Notifications</h2>
            {summary && summary.notifications_unread > 0 && (
              <Badge tone="warning">{summary.notifications_unread} unread</Badge>
            )}
          </div>
          <div className="space-y-2">
            {notifications.length === 0 && <div className="text-xs text-textDim">No notifications yet.</div>}
            {notifications.slice(0, 5).map((notif) => (
              <div key={notif.id} className={`rounded-lg border p-3 ${notif.is_read ? "border-border bg-panelMuted" : "border-accent/20 bg-accent/5"}`}>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-text">{notif.title}</div>
                  {!notif.is_read && <span className="h-2 w-2 rounded-full bg-accent" />}
                </div>
                <div className="mt-1 text-xs text-textMuted line-clamp-2">{notif.body}</div>
                <div className="mt-2 text-[11px] text-textDim">{new Date(notif.created_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};
