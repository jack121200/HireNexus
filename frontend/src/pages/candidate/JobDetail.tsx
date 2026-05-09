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

type Resume = { id: number; file_name: string; };

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

type JobDetail = {
  id: number;
  title: string;
  description: string;
  responsibilities: string | null;
  required_skills: string[];
  preferred_skills?: string[];
  minimum_experience_years: number;
  education_requirement: string | null;
  location: string | null;
  employment_type: string | null;
  status: string;
  company: { id: number; name: string; website: string; domain: string; } | null;
  hr_name: string | null;
  eligibility: Eligibility | null;
  application: { id: number; status: string; eligibility_percentage: number; } | null;
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
    phone: "", current_location: "", notice_period: "", expected_salary: "",
    portfolio_url: "", linkedin_url: "", cover_letter: "",
  });

  useEffect(() => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (resumeParam && !Number.isNaN(Number(resumeParam))) {
          setSelectedResumeId(Number(resumeParam));
        } else if (data.length) {
          setSelectedResumeId(data[0].id);
        }
      })
      .catch((err) => setError((err as Error).message));
  }, [resumeParam]);

  useEffect(() => {
    if (selectedResumeId) setSearchParams({ resume_id: String(selectedResumeId) });
  }, [selectedResumeId, setSearchParams]);

  useEffect(() => {
    if (!jobId) return;
    const load = async () => {
      setLoading(true);
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
        if (prev <= 1) { clearInterval(timer); return 0; }
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

  const submitApplication = async (jobIdValue: number) => {
    if (!selectedResumeId) return setError("Select a resume before applying.");
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

  if (!jobId) return <div className="text-danger flex h-40 items-center justify-center">Job not found.</div>;
  if (loading) return <div className="space-y-4 pt-4"><div className="h-32 rounded-xl shimmer" /><div className="grid grid-cols-3 gap-6"><div className="col-span-2 h-96 rounded-xl shimmer"/><div className="h-64 rounded-xl shimmer"/></div></div>;
  if (error || !job) return <div className="text-danger flex h-40 items-center justify-center">{error ?? "Unable to load job"}</div>;

  return (
    <div className="space-y-6 page-enter relative pb-20">
      <Link to="/candidate/jobs" className="inline-flex items-center text-xs font-medium text-textMuted hover:text-white transition-colors mb-2">
        &larr; Back to roles
      </Link>
      
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 pb-6 border-b border-border">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2 tracking-tight">{job.title}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-textMuted">
            <span className="font-medium text-white">{job.company?.name ?? "Company"}</span>
            <span>·</span>
            <span className="flex items-center gap-1">📍 {job.location || "Remote"}</span>
            <span>·</span>
            <span className="flex items-center gap-1">💼 {job.employment_type || "Full-time"}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-48 text-left">
            <Select value={selectedResumeId ?? undefined} onChange={(e) => setSelectedResumeId(Number(e.target.value))}>
              <option disabled value={undefined}>Match with...</option>
              {resumes.map((r) => <option key={r.id} value={r.id}>{r.file_name}</option>)}
            </Select>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-8 items-start">
        
        {/* Left Column - Main Details */}
        <div className="space-y-8">
          {job.application && (
            <div className="flex items-center justify-between rounded-lg border border-success/30 bg-success/10 px-4 py-3">
              <span className="text-sm font-medium text-success">You applied to this role</span>
              <Badge tone="success">{job.application.status}</Badge>
            </div>
          )}

          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-textMuted mb-4">About the Role</h2>
            <div className="prose prose-sm prose-invert max-w-none text-text leading-relaxed">
              {job.description.split("\n").map((chunk, idx) => (
                <p key={idx} className="mb-4 last:mb-0">{chunk}</p>
              ))}
            </div>
          </section>

          {job.responsibilities && (
            <section className="pt-6 border-t border-border">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-textMuted mb-4">Responsibilities</h2>
              <div className="prose prose-sm prose-invert max-w-none text-text leading-relaxed">
                {job.responsibilities.split("\n").map((chunk, idx) => (
                  <p key={idx} className="mb-2 last:mb-0">{chunk.startsWith("-") ? chunk : `• ${chunk}`}</p>
                ))}
              </div>
            </section>
          )}

          <section className="pt-6 border-t border-border">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-textMuted mb-4">Must-have Skills</h2>
            <div className="flex flex-wrap gap-2">
              {job.required_skills.length ? (
                job.required_skills.map((skill) => (
                  <span key={skill} className={`rounded-lg border px-3 py-1.5 text-xs font-medium shadow-sm ${
                    job.eligibility?.missing_skills.map(s => s.toLowerCase()).includes(skill.toLowerCase()) 
                    ? "bg-danger/10 border-danger/30 text-danger" 
                    : "bg-success/10 border-success/30 text-success"
                  }`}>
                    {job.eligibility?.missing_skills.map(s => s.toLowerCase()).includes(skill.toLowerCase()) ? "✗ " : "✓ "}{skill}
                  </span>
                ))
              ) : (
                <span className="text-sm text-textDim">No specific skills listed.</span>
              )}
            </div>
          </section>

          {job.preferred_skills && job.preferred_skills.length > 0 && (
            <section className="pt-6 border-t border-border">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-textMuted mb-4">Preferred Skills (Bonus)</h2>
              <div className="flex flex-wrap gap-2">
                {job.preferred_skills.map((skill) => (
                  <span key={skill} className="rounded-lg bg-panelMuted border border-border px-3 py-1.5 text-xs text-textMuted font-medium shadow-sm">
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          {job.eligibility && job.eligibility.skill_gaps && job.eligibility.skill_gaps.length > 0 && (
            <section className="pt-8 border-t border-border">
              <h2 className="text-xl font-bold text-text mb-4">Skill Gap Analysis & Learning Path</h2>
              <div className="space-y-4">
                {job.eligibility.skill_gaps.map((gap, i) => (
                  <div key={i} className="rounded-xl border border-warning/20 bg-panelMuted p-5">
                    <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                      <h3 className="text-lg font-bold text-text">{gap.skill}</h3>
                      <span className="text-xs bg-danger/10 text-danger px-2 py-1 rounded-full font-bold uppercase tracking-wider">Required Missing</span>
                    </div>
                    {gap.suggestion ? (
                      <div className="space-y-3 text-sm text-textMuted">
                        {gap.suggestion.personalized_note && (
                          <div className="flex items-start gap-2 text-success font-medium bg-success/5 p-3 rounded-lg border border-success/10 mb-2">
                            <span>✅</span>
                            <span>{gap.suggestion.personalized_note}</span>
                          </div>
                        )}
                        <div className="flex gap-6">
                          <div><span className="text-text font-semibold">Time:</span> {gap.suggestion.time_to_learn}</div>
                          <div><span className="text-text font-semibold">Difficulty:</span> <span className="capitalize">{gap.suggestion.difficulty}</span></div>
                        </div>
                        <div>
                          <div className="font-semibold text-text mb-1">Recommended Resources:</div>
                          <ul className="list-disc pl-5 space-y-1">
                            {gap.suggestion.resources.map((res, rIdx) => <li key={rIdx}>{res}</li>)}
                          </ul>
                        </div>
                        <div className="bg-ink p-3 rounded-lg border border-border mt-3">
                          <span className="font-semibold text-accent">Resume Tip: </span> {gap.suggestion.resume_tip}
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-textMuted">No specific learning path available for this skill.</div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right Column - Sticky Sidebar */}
        <div className="sticky top-24 space-y-4">
          
          <Card variant="surface" className="overflow-hidden">
            <div className="p-5 border-b border-border bg-panelMuted/50">
              <div className="text-xs uppercase tracking-wider text-textMuted mb-1">Your Match</div>
              {job.eligibility ? (
                <div className="flex items-baseline gap-2">
                  <div className={`text-4xl font-bold tracking-tight ${job.eligibility.eligibility_percentage >= 70 ? "text-success" : job.eligibility.eligibility_percentage >= 40 ? "text-warning" : "text-danger"}`}>
                    {job.eligibility.eligibility_percentage.toFixed(0)}<span className="text-2xl text-textDim">%</span>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-textDim">Select a resume to evaluate your fit.</div>
              )}
            </div>
            
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                <div>
                  <div className="text-xs text-textDim">Experience</div>
                  <div className="font-medium text-text mt-1">{job.minimum_experience_years}+ years</div>
                </div>
                <div>
                  <div className="text-xs text-textDim">Education</div>
                  <div className="font-medium text-text mt-1 truncate">{job.education_requirement || "Any"}</div>
                </div>
              </div>

              {job.eligibility && (
                <div className="pt-4 border-t border-border space-y-3">
                  <div className="text-xs uppercase tracking-wider text-textMuted font-semibold mb-2">Score Breakdown</div>
                  <div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-textMuted">Skills Match</span><span className="text-text font-bold">{job.eligibility.skill_match_percentage.toFixed(0)}%</span></div>
                    <div className="h-1.5 bg-panelMuted rounded-full overflow-hidden"><div className="h-full bg-success rounded-full" style={{ width: `${job.eligibility.skill_match_percentage}%` }}/></div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-textMuted">Experience</span><span className="text-text font-bold">{job.eligibility.experience_match_percentage.toFixed(0)}%</span></div>
                    <div className="h-1.5 bg-panelMuted rounded-full overflow-hidden"><div className="h-full bg-success rounded-full" style={{ width: `${job.eligibility.experience_match_percentage}%` }}/></div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-textMuted">Education</span><span className="text-text font-bold">{job.eligibility.education_match_percentage.toFixed(0)}%</span></div>
                    <div className="h-1.5 bg-panelMuted rounded-full overflow-hidden"><div className="h-full bg-success rounded-full" style={{ width: `${job.eligibility.education_match_percentage}%` }}/></div>
                  </div>
                </div>
              )}

              {job.eligibility && job.eligibility.missing_skills.length > 0 && (
                <div className="pt-4 border-t border-border">
                  <div className="text-xs text-danger font-bold mb-2 uppercase tracking-wide">Missing Key Skills</div>
                  <div className="flex flex-wrap gap-1.5">
                    {job.eligibility.missing_skills.slice(0, 5).map(s => (
                      <span key={s} className="text-[10px] font-bold border border-danger/30 text-danger px-1.5 py-0.5 rounded bg-danger/10">
                        {s}
                      </span>
                    ))}
                    {job.eligibility.missing_skills.length > 5 && (
                      <span className="text-[10px] font-bold border border-danger/30 text-danger px-1.5 py-0.5 rounded bg-danger/10">
                        +{job.eligibility.missing_skills.length - 5}
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="pt-4 border-t border-border">
                <Button 
                  className="w-full shadow-glow" 
                  onClick={() => {setApplyStep("form"); setCountdown(10);}} 
                  disabled={!selectedResumeId || !!job.application}
                >
                  {job.application ? "Already Applied" : "Apply Now"}
                </Button>
                <div className="text-[10px] text-center text-textDim mt-2">
                  You will verify your details before the AI interview begins.
                </div>
              </div>
            </div>
          </Card>

          <Card variant="surface" className="p-4">
            <div className="text-xs font-semibold text-text mb-3">Company Details</div>
            {job.company ? (
              <div className="space-y-2 text-sm text-textMuted">
                <div><span className="text-textDim">Sector:</span> {job.company.domain}</div>
                <div><span className="text-textDim">Website:</span> <a href={job.company.website} className="text-accent hover:underline" target="_blank" rel="noreferrer">{new URL(job.company.website).hostname}</a></div>
                <div className="pt-2 mt-2 border-t border-border text-xs"><span className="text-textDim">Posted by:</span> {job.hr_name}</div>
              </div>
            ) : (
              <div className="text-sm text-textDim">Company profile not available.</div>
            )}
          </Card>

        </div>
      </div>

      {/* Application Flow Modal */}
      {applyStep && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm p-4 animate-fadeIn">
          <Card variant="surface" className="w-full max-w-lg shadow-2xl scaleIn">
            
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div>
                <h2 className="text-lg font-bold text-text">Start Application</h2>
                <div className="text-[11px] text-textMuted uppercase tracking-wider">{job.title}</div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setApplyStep(null)}>✕</Button>
            </div>

            {applyStep === "form" && (
              <div className="space-y-4 pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <Input label="Phone (Optional)" value={applyDetails.phone} onChange={e => setApplyDetails(p => ({ ...p, phone: e.target.value }))} />
                  <Input label="Location (Optional)" value={applyDetails.current_location} onChange={e => setApplyDetails(p => ({ ...p, current_location: e.target.value }))} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Input label="Notice Period" placeholder="e.g. 30 days" value={applyDetails.notice_period} onChange={e => setApplyDetails(p => ({ ...p, notice_period: e.target.value }))} />
                  <Input label="Expected Salary" placeholder="e.g. 15 LPA" value={applyDetails.expected_salary} onChange={e => setApplyDetails(p => ({ ...p, expected_salary: e.target.value }))} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Input label="Portfolio Handle" placeholder="github.com/..." value={applyDetails.portfolio_url} onChange={e => setApplyDetails(p => ({ ...p, portfolio_url: e.target.value }))} />
                  <Input label="LinkedIn Handle" placeholder="in/..." value={applyDetails.linkedin_url} onChange={e => setApplyDetails(p => ({ ...p, linkedin_url: e.target.value }))} />
                </div>
                <div className="pt-2 border-t border-border flex justify-end">
                  <Button onClick={() => setApplyStep("confirm")}>Review & Continue</Button>
                </div>
              </div>
            )}

            {applyStep === "confirm" && (
              <div className="space-y-4 pt-4">
                <div className="rounded-lg bg-panelMuted border border-border p-4 text-sm">
                  <div className="flex justify-between mb-2">
                    <span className="text-textDim">Using Resume:</span>
                    <span className="font-medium text-text">{resumes.find(r => r.id === selectedResumeId)?.file_name}</span>
                  </div>
                  <div className="flex justify-between mb-2">
                    <span className="text-textDim">Match Score:</span>
                    <span className={job.eligibility && job.eligibility.eligibility_percentage >= 70 ? "text-success font-bold" : "text-warning font-bold"}>
                      {job.eligibility?.eligibility_percentage.toFixed(0) ?? 0}%
                    </span>
                  </div>
                </div>
                
                <div className="text-center p-4 bg-accent/10 border border-accent/20 rounded-lg">
                  <div className="text-lg font-bold text-accent mb-1">AI Interview Next</div>
                  <div className="text-xs text-textMuted">Submitting this directly launches your automated screening interview. Make sure your microphone is ready.</div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button variant="ghost" onClick={() => setApplyStep("form")}>Back</Button>
                  <Button onClick={() => setApplyStep("countdown")} className="bg-success hover:bg-success/90 text-white">Confirm & Launch Interview</Button>
                </div>
              </div>
            )}

            {applyStep === "countdown" && (
              <div className="py-10 text-center space-y-2">
                <div className="text-sm text-textMuted uppercase tracking-widest">Starting engine</div>
                <div className="text-6xl font-bold text-white tabular-nums drop-shadow-glow">{countdown}</div>
                <div className="text-xs text-accent animate-pulse mt-4">Connecting to intelligence node...</div>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
};
