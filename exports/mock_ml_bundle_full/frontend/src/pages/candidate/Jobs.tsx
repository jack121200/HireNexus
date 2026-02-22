import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { Select } from "../../components/Select";
import { Input } from "../../components/Input";
import { Textarea } from "../../components/Textarea";
import { apiFetch } from "../../lib/api";

type Resume = {
  id: number;
  file_name: string;
};

type JobItem = {
  id: number;
  title: string;
  location?: string | null;
  employment_type?: string | null;
  description: string;
  required_skills: string[];
  minimum_experience_years: number;
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

type JobBrowseResponse = {
  items: JobItem[];
};

type Filters = {
  search: string;
  location: string;
  employment: string;
  skills: string;
  minExperience: string;
  minEligibility: string;
  remoteOnly: boolean;
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

export const CandidateJobs = () => {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [filters, setFilters] = useState<Filters>({
    search: "",
    location: "",
    employment: "",
    skills: "",
    minExperience: "",
    minEligibility: "",
    remoteOnly: false,
  });
  const [applyJob, setApplyJob] = useState<JobItem | null>(null);
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
  const [error, setError] = useState<string | null>(null);

  const loadResumes = () => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (!selectedResumeId && data.length) {
          setSelectedResumeId(data[0].id);
        }
      })
      .catch((err) => setError((err as Error).message));
  };

  const loadJobs = (resumeId?: number | null) => {
    const query = resumeId ? `?resume_id=${resumeId}` : "";
    apiFetch<JobBrowseResponse>(`/api/candidate/jobs${query}`)
      .then((data) => setJobs(data.items))
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => {
    loadResumes();
  }, []);

  useEffect(() => {
    loadJobs(selectedResumeId);
  }, [selectedResumeId]);

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
    if (applyStep === "countdown" && countdown === 0 && applyJob && !isSubmitting) {
      void submitApplication(applyJob.id);
    }
  }, [applyStep, countdown, applyJob, isSubmitting]);

  const openApplyFlow = (job: JobItem) => {
    setApplyJob(job);
    setApplyStep("form");
    setCountdown(10);
  };

  const submitApplication = async (jobId: number) => {
    if (!selectedResumeId) {
      setError("Select a resume before applying.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await apiFetch<{ application: { id: number } }>(`/api/candidate/jobs/${jobId}/apply`, {
        method: "POST",
        body: JSON.stringify({ resume_id: selectedResumeId, details: applyDetails }),
      });
      setApplyStep(null);
      setApplyJob(null);
      navigate(`/candidate/interview/${response.application.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const searchMatch = filters.search
        ? job.title.toLowerCase().includes(filters.search.toLowerCase()) ||
          job.description.toLowerCase().includes(filters.search.toLowerCase())
        : true;
      const locationMatch = filters.location
        ? (job.location || "").toLowerCase().includes(filters.location.toLowerCase())
        : true;
      const employmentMatch = filters.employment
        ? (job.employment_type || "").toLowerCase().includes(filters.employment.toLowerCase())
        : true;
      const skillMatch = filters.skills
        ? job.required_skills.join(" ").toLowerCase().includes(filters.skills.toLowerCase())
        : true;
      const experienceMatch = filters.minExperience
        ? job.minimum_experience_years >= Number(filters.minExperience)
        : true;
      const eligibilityMatch = filters.minEligibility
        ? (job.eligibility?.eligibility_percentage ?? 0) >= Number(filters.minEligibility)
        : true;
      const remoteMatch = filters.remoteOnly
        ? (job.location || "").toLowerCase().includes("remote")
        : true;
      return (
        searchMatch &&
        locationMatch &&
        employmentMatch &&
        skillMatch &&
        experienceMatch &&
        eligibilityMatch &&
        remoteMatch
      );
    });
  }, [jobs, filters]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Job Discovery"
        subtitle="Filter roles, review eligibility, and apply with confidence."
        actions={
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
        }
      />

      <Card className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <Input
            label="Role or keyword"
            value={filters.search}
            onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
          />
          <Input
            label="Location"
            value={filters.location}
            onChange={(event) => setFilters((prev) => ({ ...prev, location: event.target.value }))}
          />
          <Input
            label="Skills (comma or space)"
            value={filters.skills}
            onChange={(event) => setFilters((prev) => ({ ...prev, skills: event.target.value }))}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Input
            label="Min experience (years)"
            type="number"
            min={0}
            value={filters.minExperience}
            onChange={(event) => setFilters((prev) => ({ ...prev, minExperience: event.target.value }))}
          />
          <Input
            label="Min eligibility %"
            type="number"
            min={0}
            max={100}
            value={filters.minEligibility}
            onChange={(event) => setFilters((prev) => ({ ...prev, minEligibility: event.target.value }))}
          />
          <Input
            label="Employment type"
            value={filters.employment}
            onChange={(event) => setFilters((prev) => ({ ...prev, employment: event.target.value }))}
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-textMuted">
            <input
              type="checkbox"
              checked={filters.remoteOnly}
              onChange={(event) => setFilters((prev) => ({ ...prev, remoteOnly: event.target.checked }))}
            />
            Remote only
          </label>
          <Button
            variant="ghost"
            onClick={() =>
              setFilters({
                search: "",
                location: "",
                employment: "",
                skills: "",
                minExperience: "",
                minEligibility: "",
                remoteOnly: false,
              })
            }
          >
            Reset Filters
          </Button>
        </div>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {filteredJobs.length === 0 && (
        <EmptyState title="No jobs found" description="Try adjusting your filters or resume selection." />
      )}
      <div className="grid gap-4">
        {filteredJobs.map((job) => (
          <Card key={job.id} className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">{job.title}</div>
                <div className="text-xs text-textMuted">
                  {job.location || "Remote"} · {job.employment_type || "Full-time"} · Min {job.minimum_experience_years} yrs
                </div>
              </div>
              {job.application ? (
                <Badge tone="success">Applied: {job.application.status}</Badge>
              ) : (
                <Button onClick={() => openApplyFlow(job)}>Apply</Button>
              )}
            </div>
            <p className="text-sm text-textMuted">{job.description}</p>
            <div className="flex flex-wrap gap-2 text-xs text-textMuted">
              {job.required_skills.map((skill) => (
                <span key={skill} className="rounded-full border border-border px-2 py-1">
                  {skill}
                </span>
              ))}
            </div>
            {job.eligibility && (
              <div className="flex flex-wrap items-center gap-4 text-sm text-textMuted">
                <span>
                  Eligibility: <span className="text-white">{job.eligibility.eligibility_percentage.toFixed(1)}%</span>
                </span>
                {job.eligibility.missing_skills.length > 0 && (
                  <span className="text-xs text-danger">
                    Missing: {job.eligibility.missing_skills.slice(0, 5).join(", ")}
                  </span>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>

      {applyJob && applyStep && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4">
          <Card className="w-full max-w-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-semibold text-white">Apply to {applyJob.title}</div>
                <div className="text-xs text-textMuted">Complete details before interview</div>
              </div>
              <Button
                variant="ghost"
                onClick={() => {
                  setApplyStep(null);
                  setApplyJob(null);
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
                  <Button onClick={() => setApplyStep("countdown")}>Submit & Start Interview</Button>
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
