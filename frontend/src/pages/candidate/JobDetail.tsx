import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { PageHeader } from "../../components/PageHeader";
import { Select } from "../../components/Select";
import { Input } from "../../components/Input";
import { Textarea } from "../../components/Textarea";
import { apiFetch } from "../../lib/api";

type Resume = {
  id: number;
  file_name: string;
};

type JobDetail = {
  id: number;
  title: string;
  description: string;
  responsibilities: string | null;
  required_skills: string[];
  minimum_experience_years: number;
  education_requirement: string | null;
  location: string | null;
  employment_type: string | null;
  status: string;
  company: {
    id: number;
    name: string;
    website: string;
    domain: string;
  } | null;
  hr_name: string | null;
  eligibility: {
    eligibility_percentage: number;
    missing_skills: string[];
  } | null;
  application: {
    id: number;
    status: string;
    eligibility_percentage: number;
  } | null;
};

type ApplyDetails = {
  phone: string;
  current_location: string;
  notice_period: string;
  expected_salary: string;
  portfolio_url: string;
  linkedin_url: string;
  cover_letter: string;
};

export const CandidateJobDetail = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const resumeParam = searchParams.get("resume_id");

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [applyStep, setApplyStep] = useState<"form" | "confirm" | "countdown" | null>(null);
  const [countdown, setCountdown] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [applyDetails, setApplyDetails] = useState<ApplyDetails>({
    phone: "",
    current_location: "",
    notice_period: "",
    expected_salary: "",
    portfolio_url: "",
    linkedin_url: "",
    cover_letter: "",
  });

  useEffect(() => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (resumeParam) {
          const parsed = Number(resumeParam);
          if (!Number.isNaN(parsed)) {
            setSelectedResumeId(parsed);
            return;
          }
        }
        if (data.length) {
          setSelectedResumeId(data[0].id);
        }
      })
      .catch((err) => setError((err as Error).message));
  }, [resumeParam]);

  useEffect(() => {
    if (selectedResumeId) {
      setSearchParams({ resume_id: String(selectedResumeId) });
    }
  }, [selectedResumeId, setSearchParams]);

  useEffect(() => {
    if (!jobId) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const query = selectedResumeId ? `?resume_id=${selectedResumeId}` : "";
        const data = await apiFetch<JobDetail>(`/api/candidate/jobs/${jobId}${query}`);
        setJob(data);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [jobId, selectedResumeId]);

  useEffect(() => {
    if (applyStep !== "countdown") return;
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [applyStep]);

  useEffect(() => {
    if (applyStep === "countdown" && countdown === 0 && job && !isSubmitting) {
      void submitApplication(job.id);
    }
  }, [applyStep, countdown, job, isSubmitting]);

  const openApplyFlow = () => {
    setApplyStep("form");
    setCountdown(10);
  };

  const submitApplication = async (jobIdValue: number) => {
    if (!selectedResumeId) {
      setError("Select a resume before applying.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await apiFetch<{ application: { id: number } }>(`/api/candidate/jobs/${jobIdValue}/apply`, {
        method: "POST",
        body: JSON.stringify({ resume_id: selectedResumeId, details: applyDetails }),
      });
      setApplyStep(null);
      navigate(`/candidate/interview/${response.application.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!jobId) {
    return <div className="text-danger">Job not found.</div>;
  }

  if (loading) {
    return <div className="text-textMuted">Loading job details...</div>;
  }

  if (error || !job) {
    return <div className="text-danger">{error ?? "Unable to load job"}</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Candidate Suite"
        title={job.title}
        subtitle={`${job.company?.name ?? "Company"} - ${job.location || "Remote"} - ${job.employment_type || "Full-time"}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Select
              label="Resume"
              value={selectedResumeId ?? undefined}
              onChange={(event) => setSelectedResumeId(Number(event.target.value))}
            >
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.file_name}
                </option>
              ))}
            </Select>
            <Link to="/candidate/jobs">
              <Button variant="ghost">Back to Jobs</Button>
            </Link>
          </div>
        }
      />

      {job.application && (
        <Card variant="glass" className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-textMuted">Application Status</div>
            <div className="text-lg font-semibold text-white">You already applied</div>
          </div>
          <Badge tone="success">{job.application.status}</Badge>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card variant="glass" className="space-y-4">
          <div className="text-xs uppercase tracking-[0.2em] text-textMuted">About Company</div>
          <div className="text-2xl font-semibold text-white">{job.company?.name ?? "Company"}</div>
          <div className="text-sm text-textMuted">
            Website: {job.company?.website ?? "N/A"}
          </div>
          <div className="text-sm text-textMuted">Domain: {job.company?.domain ?? "N/A"}</div>
          <div className="text-sm text-textMuted">Posted by: {job.hr_name ?? "HR"}</div>
        </Card>

        <Card variant="muted" className="space-y-4">
          <div className="text-xs uppercase tracking-[0.2em] text-textMuted">Eligibility Snapshot</div>
          {job.eligibility ? (
            <>
              <div className="text-3xl font-semibold text-white">{job.eligibility.eligibility_percentage.toFixed(1)}%</div>
              <div className="text-xs text-textMuted">Missing skills: {job.eligibility.missing_skills.slice(0, 6).join(", ") || "None"}</div>
            </>
          ) : (
            <div className="text-sm text-textMuted">Upload/select a resume to see eligibility.</div>
          )}
          <div className="rounded-xl border border-border/70 bg-panelMuted/70 p-4 text-xs text-textMuted">
            Minimum experience: {job.minimum_experience_years} years
            <br />
            Education: {job.education_requirement ?? "Not specified"}
          </div>
        </Card>
      </div>

      <Card variant="glass" className="space-y-4">
        <div className="text-xs uppercase tracking-[0.2em] text-textMuted">Job Description</div>
        <div className="text-sm text-text">
          {job.description.split("\n").map((chunk, idx) => (
            <p key={idx} className="mb-3 last:mb-0">
              {chunk}
            </p>
          ))}
        </div>
      </Card>

      <Card variant="glass" className="space-y-4">
        <div className="text-xs uppercase tracking-[0.2em] text-textMuted">Responsibilities</div>
        <div className="text-sm text-text">
          {job.responsibilities ? job.responsibilities : "Responsibilities will be shared during screening."}
        </div>
      </Card>

      <Card variant="glass" className="space-y-4">
        <div className="text-xs uppercase tracking-[0.2em] text-textMuted">Required Skills</div>
        <div className="flex flex-wrap gap-2 text-xs text-textMuted">
          {job.required_skills.length ? (
            job.required_skills.map((skill) => (
              <span key={skill} className="rounded-full border border-border px-2 py-1">
                {skill}
              </span>
            ))
          ) : (
            <span className="text-textMuted">No explicit skills listed.</span>
          )}
        </div>
      </Card>

      <Card variant="muted" className="space-y-4">
        <div className="text-xs uppercase tracking-[0.2em] text-textMuted">Ready to apply?</div>
        <div className="text-lg font-semibold text-white">Submit your details and start the interview flow.</div>
        <Button onClick={openApplyFlow} disabled={!selectedResumeId || !!job.application}>
          {job.application ? "Already Applied" : "Apply Now"}
        </Button>
      </Card>

      {applyStep && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4">
          <Card variant="glass" className="w-full max-w-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-semibold text-white">Apply to {job.title}</div>
                <div className="text-xs text-textMuted">Complete details before interview</div>
              </div>
              <Button
                variant="ghost"
                onClick={() => {
                  setApplyStep(null);
                }}
              >
                Close
              </Button>
            </div>

            {applyStep === "form" && (
              <div className="space-y-3">
                <Input
                  label="Phone Number"
                  value={applyDetails.phone}
                  onChange={(event) => setApplyDetails((prev) => ({ ...prev, phone: event.target.value }))}
                />
                <div className="grid gap-3 md:grid-cols-2">
                  <Input
                    label="Current Location"
                    value={applyDetails.current_location}
                    onChange={(event) => setApplyDetails((prev) => ({ ...prev, current_location: event.target.value }))}
                  />
                  <Input
                    label="Notice Period"
                    value={applyDetails.notice_period}
                    onChange={(event) => setApplyDetails((prev) => ({ ...prev, notice_period: event.target.value }))}
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Input
                    label="Expected Salary"
                    value={applyDetails.expected_salary}
                    onChange={(event) => setApplyDetails((prev) => ({ ...prev, expected_salary: event.target.value }))}
                  />
                  <Input
                    label="Portfolio URL"
                    value={applyDetails.portfolio_url}
                    onChange={(event) => setApplyDetails((prev) => ({ ...prev, portfolio_url: event.target.value }))}
                  />
                </div>
                <Input
                  label="LinkedIn URL"
                  value={applyDetails.linkedin_url}
                  onChange={(event) => setApplyDetails((prev) => ({ ...prev, linkedin_url: event.target.value }))}
                />
                <Textarea
                  label="Cover Note"
                  value={applyDetails.cover_letter}
                  onChange={(event) => setApplyDetails((prev) => ({ ...prev, cover_letter: event.target.value }))}
                />
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" onClick={() => setApplyStep("confirm")}>
                    Continue
                  </Button>
                </div>
              </div>
            )}

            {applyStep === "confirm" && (
              <div className="space-y-3 text-sm text-textMuted">
                <div className="rounded-lg border border-border bg-panelMuted p-3">
                  <div className="text-xs uppercase text-textMuted">Application Summary</div>
                  <div className="mt-2">Resume: {resumes.find((resume) => resume.id === selectedResumeId)?.file_name}</div>
                  <div>Phone: {applyDetails.phone || "Not provided"}</div>
                  <div>Location: {applyDetails.current_location || "Not provided"}</div>
                  <div>Notice: {applyDetails.notice_period || "Not provided"}</div>
                  <div>Expected Salary: {applyDetails.expected_salary || "Not provided"}</div>
                  <div>Portfolio: {applyDetails.portfolio_url || "Not provided"}</div>
                  <div>LinkedIn: {applyDetails.linkedin_url || "Not provided"}</div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setApplyStep("form")}>Back</Button>
                  <Button onClick={() => setApplyStep("countdown")}>Submit and Start Interview</Button>
                </div>
              </div>
            )}

            {applyStep === "countdown" && (
              <div className="space-y-3 text-center">
                <div className="text-sm text-textMuted">Interview starts in</div>
                <div className="text-4xl font-semibold text-white">{countdown}s</div>
                <div className="text-xs text-textMuted">Get ready. We are preparing your AI interviewer.</div>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
};
