import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";

import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch } from "../../lib/api";

type ApplicantItem = {
  application: { id: number; status: string; eligibility_percentage: number; skill_match_percentage: number; experience_match_percentage: number; education_match_percentage: number; missing_skills: string[]; };
  candidate: { id: number; full_name: string; email: string; skills: string[]; estimated_experience_years: number | null; education_level: string | null; };
  ai_interview: { interview_id: number | null; overall_score: number | null; confidence_score: number | null; status: string | null; report_ready: boolean; report_pdf_url: string | null; completed_at: string | null; };
};

type HrInterviewReport = {
  interview_id: number; status: string; type: string; overall_score: number | null; confidence_score: number | null; summary: string;
  strengths: string[]; weaknesses: string[]; improvements: string[]; skill_gaps: string[];
  per_question: Array<{ id: string; question: string; answer: string; score: number; category: string; difficulty: string; feedback: string; rubric_points: string[]; }>;
  transcript_highlights: string[]; report_pdf_url: string | null; completed_at: string | null; report_ready: boolean;
};

export const HrApplicants = () => {
  const { jobId } = useParams();
  const [items, setItems] = useState<ApplicantItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedApplicationId, setSelectedApplicationId] = useState<number | null>(null);
  const [selectedReport, setSelectedReport] = useState<HrInterviewReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  const loadApplicants = () => {
    if (!jobId) return;
    apiFetch<{ items: ApplicantItem[] }>(`/api/hr/job/${jobId}/applicants`)
      .then((data) => setItems(data.items))
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => { loadApplicants(); }, [jobId]);

  const updateStatus = async (applicationId: number, status: "shortlisted" | "rejected") => {
    try {
      await apiFetch(`/api/hr/applications/${applicationId}/status`, { method: "POST", body: JSON.stringify({ status }) });
      loadApplicants();
    } catch (err) { setError((err as Error).message); }
  };

  const openReport = async (applicationId: number) => {
    setError(null);
    setSelectedApplicationId(applicationId);
    setReportLoading(true);
    try {
      const data = await apiFetch<{ report: HrInterviewReport }>(`/api/hr/job/${jobId}/applicants/${applicationId}/ai-interview-report`);
      setSelectedReport(data.report);
    } catch (err) {
      setSelectedReport(null);
      setError((err as Error).message);
    } finally {
      setReportLoading(false);
    }
  };

  const selectedApplicant = useMemo(() => items.find((i) => i.application.id === selectedApplicationId) ?? null, [items, selectedApplicationId]);

  if (!jobId) return <EmptyState title="Select a job" description="Open a job from Jobs & Applicants to view candidates." />;

  return (
    <div className="space-y-6 page-enter pb-20">
      <Link to="/hr/jobs" className="inline-flex items-center text-xs font-medium text-textMuted hover:text-white transition-colors mb-2">
        &larr; Back to roles
      </Link>
      
      <PageHeader
        kicker="HR Intelligence"
        title="Applicant Pipeline"
        subtitle="Review candidates side-by-side with AI interview analysis."
      />
      
      {error && <div className="p-3 text-sm text-danger border border-danger/30 bg-danger/10 rounded-lg">{error}</div>}

      <div className="grid lg:grid-cols-[1.2fr_1.5fr] gap-6 items-start h-[calc(100vh-200px)]">
        
        {/* Left: Applicant List */}
        <Card variant="surface" className="flex flex-col h-full !p-0 overflow-hidden">
          <div className="p-4 border-b border-border bg-panelMuted flex items-center justify-between z-10 sticky top-0">
            <h2 className="text-sm font-semibold text-text uppercase tracking-wider">Candidates ({items.length})</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-0 scrollbar-thin">
            {items.length === 0 ? (
              <div className="p-6">
                <EmptyState title="Pipeline empty" description="Waiting for candidates to apply or finish interviews." />
              </div>
            ) : items.map((item) => (
              <div 
                key={item.application.id} 
                className={`p-5 border-b border-border transition-colors cursor-pointer block-link
                  ${selectedApplicationId === item.application.id ? "bg-accent/10 border-l-2 border-l-accent" : "hover:bg-panelMuted"}
                `}
                onClick={() => openReport(item.application.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-lg font-bold text-white mb-0.5">{item.candidate.full_name}</h3>
                    <div className="text-xs text-textDim">{item.candidate.email}</div>
                  </div>
                  {item.application.status === "shortlisted" && <Badge tone="success">Shortlisted</Badge>}
                  {item.application.status === "rejected" && <Badge tone="danger">Rejected</Badge>}
                  {item.application.status === "applied" && <Badge tone="default">Ready</Badge>}
                </div>

                <div className="grid grid-cols-2 gap-3 my-3 text-xs">
                  <div className="bg-panelMuted rounded-md p-2 border border-border">
                    <div className="text-textDim uppercase tracking-widest text-[10px] mb-1">Fit Score</div>
                    <div className={`text-xl font-bold ${item.application.eligibility_percentage >= 70 ? 'text-success' : 'text-warning'}`}>
                      {item.application.eligibility_percentage.toFixed(0)}%
                    </div>
                  </div>
                  <div className="bg-panelMuted rounded-md p-2 border border-border">
                    <div className="text-textDim uppercase tracking-widest text-[10px] mb-1">AI Interview</div>
                    <div className={`text-xl font-bold ${item.ai_interview.overall_score && item.ai_interview.overall_score >= 70 ? 'text-success' : 'text-text'}`}>
                      {item.ai_interview.overall_score ?? "Pending"}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-2">
                  <Button variant="ghost" size="sm" className="flex-1 hover:text-success hover:bg-success/10 border border-success/20" onClick={(e) => { e.stopPropagation(); updateStatus(item.application.id, "shortlisted"); }}>
                    Shortlist
                  </Button>
                  <Button variant="ghost" size="sm" className="flex-1 hover:text-danger hover:bg-danger/10 border border-danger/20" onClick={(e) => { e.stopPropagation(); updateStatus(item.application.id, "rejected"); }}>
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Right: AI Report Viewer */}
        <Card variant="surface" className="flex flex-col h-full !p-0 overflow-hidden relative">
          <div className="p-4 border-b border-border bg-panelMuted flex items-center justify-between z-10 sticky top-0 shrink-0">
            <h2 className="text-sm font-semibold text-text uppercase tracking-wider">AI Insight Engine</h2>
            {selectedReport?.report_pdf_url && (
              <Button size="sm" variant="secondary" onClick={() => window.open(`${baseUrl}${selectedReport.report_pdf_url}`, "_blank")}>
                Download PDF
              </Button>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
            {!selectedApplicationId ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-textMuted space-y-4">
                <div className="text-4xl grayscale opacity-50">🤖</div>
                <div>Select a candidate to load their AI interview report.</div>
              </div>
            ) : reportLoading ? (
              <div className="space-y-6">
                <div className="h-24 rounded-lg shimmer" />
                <div className="h-40 rounded-lg shimmer" />
                <div className="h-32 rounded-lg shimmer" />
              </div>
            ) : !selectedReport ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-textMuted space-y-4">
                <div className="text-4xl text-warning opacity-80">⏳</div>
                <div className="text-white font-medium">Interview processing...</div>
                <div className="text-xs">The AI agent is still compiling the performance matrix. Check back soon.</div>
              </div>
            ) : (
              <div className="space-y-8 pb-10 animate-fadeIn">
                
                {/* Header Profile */}
                <div className="flex flex-wrap gap-4 items-end justify-between border-b border-border pb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">{selectedApplicant?.candidate.full_name}</h2>
                    <div className="text-sm text-textDim flex items-center gap-2">
                      <span className="uppercase text-[10px] tracking-widest border border-border px-1.5 py-0.5 rounded bg-panelMuted">ID #{selectedReport.interview_id}</span>
                      <span>{new Date(selectedReport.completed_at || "").toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-right">
                      <div className="text-[10px] uppercase text-textDim tracking-widest">Aggregate Score</div>
                      <div className={`text-4xl font-bold ${selectedReport.overall_score && selectedReport.overall_score >= 70 ? 'text-success' : 'text-warning'}`}>
                        {selectedReport.overall_score}<span className="text-xl text-textDim">%</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] uppercase text-textDim tracking-widest">AI Confidence</div>
                      <div className="text-4xl font-bold text-accent">
                        {selectedReport.confidence_score}<span className="text-xl text-textDim">%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI Summary */}
                <section className="space-y-3">
                  <h3 className="text-xs font-semibold text-textMuted uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-accent animate-pulse"></span> Executive Summary
                  </h3>
                  <p className="text-sm text-text leading-relaxed bg-accent/5 p-4 rounded-lg border border-accent/10">
                    {selectedReport.summary || "No summary formulated."}
                  </p>
                </section>

                {/* SWOT Grid */}
                <div className="grid md:grid-cols-2 gap-4">
                  <Card variant="surface" className="!p-4 bg-success/5 border-success/10 space-y-3">
                    <h3 className="text-xs font-semibold text-success uppercase tracking-widest flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-success"></span> Core Strengths
                    </h3>
                    <ul className="space-y-2">
                      {(selectedReport.strengths.length ? selectedReport.strengths : ["N/A"]).map((item, idx) => (
                        <li key={idx} className="text-xs text-text flex items-start gap-2"><span className="text-success mt-0.5">✓</span> <span>{item}</span></li>
                      ))}
                    </ul>
                  </Card>
                  <Card variant="surface" className="!p-4 bg-danger/5 border-danger/10 space-y-3">
                    <h3 className="text-xs font-semibold text-danger uppercase tracking-widest flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-danger"></span> Identified Weaknesses
                    </h3>
                    <ul className="space-y-2">
                      {(selectedReport.weaknesses.length ? selectedReport.weaknesses : ["N/A"]).map((item, idx) => (
                        <li key={idx} className="text-xs text-text flex items-start gap-2"><span className="text-danger mt-0.5">✕</span> <span>{item}</span></li>
                      ))}
                    </ul>
                  </Card>
                </div>

                {/* Questions Log */}
                <section className="space-y-4">
                  <h3 className="text-xs font-semibold text-textMuted uppercase tracking-widest pt-4 border-t border-border">Session Transcript & Feedback</h3>
                  <div className="space-y-4">
                    {selectedReport.per_question.length ? selectedReport.per_question.map((item, idx) => (
                      <Card key={idx} variant="surface" className="!p-4 border border-border/50">
                        <div className="flex items-start gap-3">
                          <div className="shrink-0 w-6 h-6 rounded-full bg-panelMuted border border-border flex items-center justify-center text-[10px] font-mono text-textDim">
                            {idx + 1}
                          </div>
                          <div className="flex-1 space-y-3">
                            <div className="font-medium text-sm text-white mb-2">{item.question}</div>
                            
                            <div className="pl-3 border-l-2 border-border/50">
                              <div className="text-[10px] text-textDim uppercase tracking-widest mb-1">Candidate Transcript</div>
                              <div className="text-xs text-text leading-relaxed font-mono bg-black/20 p-3 rounded">{item.answer || "No response."}</div>
                            </div>
                            
                            <div className="bg-panelMuted/50 p-3 rounded-md pt-2">
                              <div className="flex justify-between items-center mb-1">
                                <div className="text-[10px] text-accent uppercase tracking-widest">AI Feedback</div>
                                <div className="text-xs font-bold font-mono text-white px-2 py-0.5 bg-black rounded">Score: {item.score}/100</div>
                              </div>
                              <div className="text-xs text-textMuted">{item.feedback}</div>
                            </div>
                          </div>
                        </div>
                      </Card>
                    )) : (
                      <div className="text-sm text-textDim italic p-4 text-center border border-dashed border-border rounded-lg">Log unavailable or corrupted.</div>
                    )}
                  </div>
                </section>
                
              </div>
            )}
          </div>
        </Card>

      </div>
    </div>
  );
};
