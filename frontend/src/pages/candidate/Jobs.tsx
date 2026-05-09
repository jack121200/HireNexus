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

type Resume = { id: number; file_name: string };

type SkillGap = {
  skill: string;
  gap_type: "hard" | "soft";
  suggestion?: {
    time_to_learn: string;
    difficulty: string;
    resources: string[];
    resume_tip: string;
    personalized_note?: string | null;
  };
};

type Eligibility = {
  eligibility_percentage: number;
  skill_match_percentage: number;
  experience_match_percentage: number;
  education_match_percentage: number;
  missing_skills: string[];
  required_skills: string[];
  suggestions: string[];
  skill_gaps?: SkillGap[];
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
  preferred_skills?: string[];
  minimum_experience_years: number;
  eligibility: Eligibility | null;
  application?: { id: number; status: string; eligibility_percentage: number } | null;
};

type JobBrowseResponse = {
  items: JobItem[];
  meta: { page: number; page_size: number; total: number; total_pages: number };
};

// ── Eligibility badge helper ──────────────────────────────────────────────────
function eligibilityMeta(pct: number) {
  if (pct >= 75) return { label: "Strong Match", color: "#10b981", bg: "rgba(16,185,129,0.1)", border: "rgba(16,185,129,0.3)" };
  if (pct >= 55) return { label: "Good Match", color: "#3b82f6", bg: "rgba(59,130,246,0.1)", border: "rgba(59,130,246,0.3)" };
  if (pct >= 35) return { label: "Partial Match", color: "#f59e0b", bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)" };
  return { label: "Low Match", color: "#ef4444", bg: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.3)" };
}

// ── Score bar ─────────────────────────────────────────────────────────────────
function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 75 ? "#10b981" : value >= 50 ? "#3b82f6" : value >= 30 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12, color: "var(--color-textMuted)" }}>
        <span>{label}</span>
        <span style={{ fontWeight: 700, color }}>{value.toFixed(0)}%</span>
      </div>
      <div style={{ background: "var(--color-panelMuted)", borderRadius: 99, height: 6, overflow: "hidden" }}>
        <div style={{ width: `${value}%`, background: color, height: "100%", borderRadius: 99, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

// ── Expandable Job Card ───────────────────────────────────────────────────────
function JobCard({ job, resumeId }: { job: JobItem; resumeId: number | null }) {
  const [expanded, setExpanded] = useState(false);
  const elig = job.eligibility;
  const meta = elig ? eligibilityMeta(elig.eligibility_percentage) : null;

  // Which required skills candidate has vs missing
  const matchedSkills = elig
    ? job.required_skills.filter(s => !elig.missing_skills.map(m => m.toLowerCase()).includes(s.toLowerCase()))
    : [];

  return (
    <Card variant="surface" className="card-interactive" style={{ padding: 0, overflow: "hidden" }}>
      {/* Main clickable row */}
      <Link
        to={`/candidate/jobs/${job.id}?resume_id=${resumeId ?? ""}`}
        className="block block-link group"
        style={{ padding: "20px 24px" }}
      >
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          {/* Left: title + meta */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
              <h3 style={{ fontSize: 17, fontWeight: 700, margin: 0 }} className="text-text group-hover:text-accent transition-colors">
                {job.title}
              </h3>
              {job.application && <Badge tone="success">Applied</Badge>}
            </div>
            <div style={{ fontSize: 13, color: "var(--color-textMuted)", marginBottom: 10 }}>
              <span style={{ color: "var(--color-text)", fontWeight: 600 }}>{job.company || "Company"}</span>
              {" · "}{job.location || "Remote"}{" · "}{job.employment_type || "Full-time"}
            </div>
            <p style={{ fontSize: 13, color: "var(--color-textDim)", margin: "0 0 12px", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
              {job.description}
            </p>

            {/* Skill chips */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {matchedSkills.slice(0, 4).map(s => (
                <span key={s} style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)", color: "#10b981", borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 600 }}>
                  ✓ {s}
                </span>
              ))}
              {elig && elig.missing_skills.slice(0, 3).map(s => (
                <span key={s} style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", color: "#ef4444", borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 600 }}>
                  ✗ {s}
                </span>
              ))}
              {!elig && job.required_skills.slice(0, 5).map(s => (
                <span key={s} style={{ background: "var(--color-panelMuted)", border: "1px solid var(--color-border)", color: "var(--color-textMuted)", borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 500 }}>
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Right: match score */}
          <div style={{ textAlign: "right", minWidth: 120, flexShrink: 0 }}>
            {meta && elig ? (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: "var(--color-textDim)", marginBottom: 4 }}>Match Score</div>
                <div style={{
                  display: "inline-block", padding: "6px 14px", borderRadius: 10,
                  background: meta.bg, border: `1px solid ${meta.border}`, color: meta.color,
                  fontWeight: 800, fontSize: 22,
                }}>
                  {elig.eligibility_percentage.toFixed(0)}%
                </div>
                <div style={{ fontSize: 11, color: meta.color, marginTop: 4, fontWeight: 600 }}>{meta.label}</div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: "var(--color-textDim)" }}>Select resume to see fit</div>
            )}
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-accent)", display: "inline-flex", alignItems: "center", gap: 3 }} className="group-hover:translate-x-1 transition-transform">
              View details →
            </span>
          </div>
        </div>
      </Link>

      {/* Expandable analysis panel */}
      {elig && (
        <>
          <button
            onClick={() => setExpanded(x => !x)}
            style={{
              width: "100%", padding: "8px 24px", background: "var(--color-panelMuted)",
              borderTop: "1px solid var(--color-border)", cursor: "pointer",
              fontSize: 12, color: "var(--color-textMuted)", fontWeight: 600,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              border: "none", outline: "none",
            }}
          >
            <span>{expanded ? "▲" : "▼"}</span>
            {expanded ? "Hide Analysis" : "Show Full Analysis"}
          </button>

          {expanded && (
            <div style={{ padding: "20px 24px", borderTop: "1px solid var(--color-border)" }}>
              {/* Score Bars */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: "var(--color-text)" }}>Score Breakdown</div>
                <ScoreBar label="Skills Match" value={elig.skill_match_percentage} />
                <ScoreBar label="Experience" value={elig.experience_match_percentage} />
                <ScoreBar label="Education" value={elig.education_match_percentage} />
              </div>

              {/* Gap Analysis */}
              {elig.skill_gaps && elig.skill_gaps.length > 0 && (
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: "var(--color-text)" }}>
                    Skill Gaps &amp; How to Close Them
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {elig.skill_gaps.slice(0, 4).map((gap, i) => (
                      <div key={i} style={{
                        background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.15)",
                        borderRadius: 10, padding: "12px 16px",
                      }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, flexWrap: "wrap", gap: 4 }}>
                          <span style={{ fontWeight: 700, color: "var(--color-text)", fontSize: 13 }}>{gap.skill}</span>
                          <span style={{ fontSize: 11, background: "rgba(239,68,68,0.1)", color: "#ef4444", borderRadius: 99, padding: "2px 8px", fontWeight: 600 }}>Missing</span>
                        </div>
                        {gap.suggestion && (
                          <div style={{ fontSize: 12, color: "var(--color-textMuted)" }}>
                            {gap.suggestion.personalized_note && (
                              <div style={{ color: "#10b981", marginBottom: 4, fontWeight: 500 }}>{gap.suggestion.personalized_note}</div>
                            )}
                            <div>⏱ <strong>Time to learn:</strong> {gap.suggestion.time_to_learn}</div>
                            <div style={{ marginTop: 3 }}>📝 <strong>Resume tip:</strong> {gap.suggestion.resume_tip}</div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  {elig.skill_gaps.length > 4 && (
                    <Link to={`/candidate/jobs/${job.id}?resume_id=${resumeId ?? ""}`} style={{ fontSize: 12, color: "var(--color-accent)", display: "block", marginTop: 8 }}>
                      View {elig.skill_gaps.length - 4} more gaps with full learning resources →
                    </Link>
                  )}
                </div>
              )}

              {/* Preferred skills */}
              {job.preferred_skills && job.preferred_skills.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: "var(--color-text)" }}>Preferred (Bonus) Skills</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {job.preferred_skills.map(s => (
                      <span key={s} style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)", color: "#3b82f6", borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 500 }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export const CandidateJobs = () => {
  const pageSize = 10;
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [page, setPage] = useState(1);
  const [meta, setMeta] = useState<JobBrowseResponse["meta"] | null>(null);
  const [filters, setFilters] = useState({ search: "", location: "", employment: "", skills: "", minExperience: "", minEligibility: "", remoteOnly: false });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (data.length) setSelectedResumeId(data[0].id);
      })
      .catch((err) => setError((err as Error).message));
  }, []);

  useEffect(() => {
    const loadJobs = async () => {
      setLoading(true);
      const params = new URLSearchParams();
      if (selectedResumeId) params.set("resume_id", String(selectedResumeId));
      params.set("page", String(page));
      params.set("page_size", String(pageSize));

      try {
        const data = await apiFetch<JobBrowseResponse>(`/api/candidate/jobs?${params.toString()}`);
        setJobs(data.items);
        setMeta(data.meta);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    loadJobs();
  }, [selectedResumeId, page]);

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const s = filters.search.toLowerCase();
      if (s && !(job.title.toLowerCase().includes(s) || job.description.toLowerCase().includes(s))) return false;
      const l = filters.location.toLowerCase();
      if (l && !(job.location || "").toLowerCase().includes(l)) return false;
      const sk = filters.skills.toLowerCase();
      if (sk && !job.required_skills.join(" ").toLowerCase().includes(sk)) return false;
      if (filters.minExperience && job.minimum_experience_years < Number(filters.minExperience)) return false;
      if (filters.minEligibility && (job.eligibility?.eligibility_percentage ?? 0) < Number(filters.minEligibility)) return false;
      if (filters.remoteOnly && !(job.location || "").toLowerCase().includes("remote")) return false;
      return true;
    });
  }, [jobs, filters]);

  const totalPages = meta?.total_pages ?? 1;

  return (
    <div className="space-y-6 page-enter">
      <PageHeader
        kicker="Candidate Suite"
        title="Job Discovery"
        subtitle="Browse roles, see your AI match score, and get a personalised gap analysis before applying."
        actions={
          <div style={{ minWidth: 200 }}>
            <Select value={selectedResumeId ?? undefined} onChange={(e) => setSelectedResumeId(Number(e.target.value))}>
              <option disabled value={undefined}>Select Resume for Matching</option>
              {resumes.map((r) => <option key={r.id} value={r.id}>{r.file_name}</option>)}
            </Select>
          </div>
        }
      />

      {/* Filters */}
      <Card variant="surface" className="space-y-4">
        <div className="text-sm font-semibold text-text mb-2">Search Filters</div>
        <div className="grid gap-3 md:grid-cols-4">
          <Input placeholder="Role or keyword" value={filters.search} onChange={(e) => setFilters(p => ({ ...p, search: e.target.value }))} />
          <Input placeholder="Location" value={filters.location} onChange={(e) => setFilters(p => ({ ...p, location: e.target.value }))} />
          <Input placeholder="Skills" value={filters.skills} onChange={(e) => setFilters(p => ({ ...p, skills: e.target.value }))} />
          <Input placeholder="Min eligibility %" type="number" value={filters.minEligibility} onChange={(e) => setFilters(p => ({ ...p, minEligibility: e.target.value }))} />
        </div>
        <div className="flex flex-wrap items-center justify-between pt-2">
          <label className="flex items-center gap-2 text-sm text-textMuted cursor-pointer hover:text-text transition-colors">
            <input type="checkbox" className="accent-accent" checked={filters.remoteOnly} onChange={(e) => setFilters(p => ({ ...p, remoteOnly: e.target.checked }))} />
            Remote only
          </label>
          <Button size="sm" variant="ghost" onClick={() => setFilters({ search: "", location: "", employment: "", skills: "", minExperience: "", minEligibility: "", remoteOnly: false })}>
            Clear Filters
          </Button>
        </div>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <div key={i} className="h-40 rounded-xl shimmer" />)}
        </div>
      ) : filteredJobs.length === 0 ? (
        <EmptyState title="No jobs found" description="Try adjusting your filters or selecting a different resume." />
      ) : (
        <div className="space-y-4">
          {filteredJobs.map((job) => (
            <JobCard key={job.id} job={job} resumeId={selectedResumeId} />
          ))}
        </div>
      )}

      {meta && meta.total_pages > 1 && (
        <div className="flex items-center justify-between border-t border-border pt-4">
          <div className="text-sm text-textMuted">
            Page <span className="text-text font-medium">{page}</span> of {totalPages}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
            <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
};
