import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { Select } from "../../components/Select";
import { Input } from "../../components/Input";
import { apiFetch } from "../../lib/api";

type Resume = {
  id: number;
  file_name: string;
};

type JobItem = {
  id: number | string;
  title: string;
  company?: string | null;
  hr_name?: string | null;
  location?: string | null;
  employment_type?: string | null;
  description: string;
  required_skills: string[];
  minimum_experience_years: number;
  source?: string | null;
  external?: boolean;
  apply_url?: string | null;
  eligibility: {
    eligibility_percentage: number;
    missing_skills: string[];
  } | null;
  application?: {
    id: number;
    status: string;
    eligibility_percentage: number;
  } | null;
};

type JobBrowseResponse = {
  items: JobItem[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
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

export const CandidateJobs = () => {
  const pageSize = 10;
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [page, setPage] = useState(1);
  const [meta, setMeta] = useState<JobBrowseResponse["meta"] | null>(null);
  const [filters, setFilters] = useState<Filters>({
    search: "",
    location: "",
    employment: "",
    skills: "",
    minExperience: "",
    minEligibility: "",
    remoteOnly: false,
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

  const loadJobs = (resumeId: number | null, pageNumber: number) => {
    const params = new URLSearchParams();
    if (resumeId) {
      params.set("resume_id", String(resumeId));
    }
    params.set("page", String(pageNumber));
    params.set("page_size", String(pageSize));
    const query = params.toString() ? `?${params.toString()}` : "";
    setError(null);
    apiFetch<JobBrowseResponse>(`/api/candidate/jobs${query}`)
      .then((data) => {
        setJobs(data.items);
        setMeta(data.meta);
      })
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => {
    loadResumes();
  }, []);

  useEffect(() => {
    loadJobs(selectedResumeId, page);
  }, [selectedResumeId, page]);

  useEffect(() => {
    setPage((prev) => (prev === 1 ? prev : 1));
  }, [selectedResumeId]);

  useEffect(() => {
    if (meta && page > meta.total_pages && meta.total_pages > 0) {
      setPage(meta.total_pages);
    }
  }, [meta, page]);

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

  const totalPages = meta?.total_pages ?? 1;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Candidate Suite"
        title="Job Discovery"
        subtitle="Browse roles, review eligibility, and view full job details before applying."
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

      <Card variant="glass" className="space-y-4">
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
          <Card key={job.id} variant="muted" className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">{job.title}</div>
                <div className="text-xs text-textMuted">
                  {job.company ? `${job.company} - ` : ""}
                  {job.location || "Remote"} - {job.employment_type || "Full-time"} - Min {job.minimum_experience_years} yrs
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                {job.application && <Badge tone="success">Applied: {job.application.status}</Badge>}
                {job.hr_name && <span className="text-xs text-textMuted">Posted by {job.hr_name}</span>}
                <Link to={`/candidate/jobs/${job.id}?resume_id=${selectedResumeId ?? ""}`}>
                  <Button variant="secondary">View Details</Button>
                </Link>
              </div>
            </div>
            <p className="text-sm text-textMuted">
              {job.description.length > 180 ? `${job.description.slice(0, 180)}...` : job.description}
            </p>
            {job.required_skills.length > 0 && (
              <div className="flex flex-wrap gap-2 text-xs text-textMuted">
                {job.required_skills.map((skill) => (
                  <span key={skill} className="rounded-full border border-border px-2 py-1">
                    {skill}
                  </span>
                ))}
              </div>
            )}
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
      {meta && meta.total_pages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-textMuted">
            Page {page} of {totalPages} · {meta.total} total jobs
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            >
              Prev
            </Button>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
              <Button
                key={pageNumber}
                variant={pageNumber === page ? "primary" : "ghost"}
                size="sm"
                onClick={() => setPage(pageNumber)}
              >
                {pageNumber}
              </Button>
            ))}
            <Button
              variant="ghost"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
