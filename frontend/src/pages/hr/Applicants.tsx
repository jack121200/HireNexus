import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch } from "../../lib/api";

type ApplicantItem = {
  application: {
    id: number;
    status: string;
    eligibility_percentage: number;
    skill_match_percentage: number;
    experience_match_percentage: number;
    education_match_percentage: number;
    missing_skills: string[];
  };
  candidate: {
    id: number;
    full_name: string;
    email: string;
    skills: string[];
    estimated_experience_years: number | null;
    education_level: string | null;
  };
  ai_interview: {
    interview_id: number | null;
    overall_score: number | null;
    confidence_score: number | null;
    status: string | null;
    report_ready: boolean;
    report_pdf_url: string | null;
    completed_at: string | null;
  };
};

type HrInterviewReport = {
  interview_id: number;
  status: string;
  type: string;
  overall_score: number | null;
  confidence_score: number | null;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  improvements: string[];
  skill_gaps: string[];
  per_question: Array<{
    id: string;
    question: string;
    answer: string;
    score: number;
    category: string;
    difficulty: string;
    feedback: string;
    rubric_points: string[];
  }>;
  transcript_highlights: string[];
  report_pdf_url: string | null;
  completed_at: string | null;
  report_ready: boolean;
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

  useEffect(() => {
    loadApplicants();
  }, [jobId]);

  if (!jobId) {
    return <EmptyState title="Select a job" description="Open a job from Jobs & Applicants to view candidates." />;
  }

  const updateStatus = async (applicationId: number, status: "shortlisted" | "rejected") => {
    try {
      await apiFetch(`/api/hr/applications/${applicationId}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      loadApplicants();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const openReport = async (applicationId: number) => {
    setError(null);
    setSelectedApplicationId(applicationId);
    setReportLoading(true);
    try {
      const data = await apiFetch<{ report: HrInterviewReport }>(
        `/api/hr/job/${jobId}/applicants/${applicationId}/ai-interview-report`
      );
      setSelectedReport(data.report);
    } catch (err) {
      setSelectedReport(null);
      setError((err as Error).message);
    } finally {
      setReportLoading(false);
    }
  };

  const selectedApplicant = useMemo(
    () => items.find((item) => item.application.id === selectedApplicationId) ?? null,
    [items, selectedApplicationId]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="HR Suite"
        title="Applicants"
        subtitle="Review candidate eligibility and AI interview reports in one place."
      />
      {error && <p className="text-danger">{error}</p>}
      {items.length === 0 && (
        <EmptyState title="No applicants yet" description="Applications will appear as candidates apply." />
      )}
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="grid gap-4">
          {items.map((item) => (
            <Card key={item.application.id} variant="glass" className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-semibold text-white">{item.candidate.full_name}</div>
                  <div className="text-xs text-textMuted">{item.candidate.email}</div>
                </div>
                <Badge tone="default">{item.application.status}</Badge>
              </div>
              <div className="grid gap-2 text-sm text-textMuted md:grid-cols-3">
                <div>Eligibility: {item.application.eligibility_percentage.toFixed(1)}%</div>
                <div>Skill Match: {item.application.skill_match_percentage.toFixed(1)}%</div>
                <div>Experience: {item.application.experience_match_percentage.toFixed(1)}%</div>
              </div>
              <div className="text-xs text-textMuted">
                Missing Skills: {item.application.missing_skills.length ? item.application.missing_skills.join(", ") : "None"}
              </div>
              <div className="grid gap-2 text-sm text-textMuted md:grid-cols-2">
                <div>AI Interview: {item.ai_interview.status || "pending"}</div>
                <div>Score: {item.ai_interview.overall_score ?? "N/A"}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" onClick={() => updateStatus(item.application.id, "shortlisted")}>
                  Shortlist
                </Button>
                <Button variant="danger" onClick={() => updateStatus(item.application.id, "rejected")}>
                  Reject
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => openReport(item.application.id)}
                  disabled={!item.ai_interview.report_ready}
                >
                  Review AI Interview Report
                </Button>
              </div>
            </Card>
          ))}
        </div>

        <Card variant="muted" className="space-y-4">
          <div className="text-lg font-semibold text-white">AI Interview Review</div>
          {!selectedApplicationId && <div className="text-sm text-textMuted">Choose an applicant to review report.</div>}
          {selectedApplicationId && reportLoading && <div className="text-sm text-textMuted">Loading report...</div>}
          {selectedApplicationId && !reportLoading && !selectedReport && (
            <div className="text-sm text-textMuted">Report not available yet for this applicant.</div>
          )}
          {selectedReport && (
            <>
              <div className="rounded-xl border border-border bg-panelMuted p-3 text-sm text-textMuted">
                <div className="text-white">{selectedApplicant?.candidate.full_name ?? "Candidate"}</div>
                <div>Interview #{selectedReport.interview_id}</div>
                <div>Status: {selectedReport.status}</div>
                <div>Overall Score: {selectedReport.overall_score ?? "N/A"}</div>
                <div>Confidence: {selectedReport.confidence_score ?? "N/A"}</div>
                {selectedReport.report_pdf_url && (
                  <div className="mt-2">
                    <Button
                      variant="secondary"
                      onClick={() => window.open(`${baseUrl}${selectedReport.report_pdf_url}`, "_blank")}
                    >
                      Download PDF
                    </Button>
                  </div>
                )}
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-xs text-textMuted">Summary</div>
                  <div className="text-text">{selectedReport.summary || "No summary available"}</div>
                </div>
                <div>
                  <div className="text-xs text-textMuted">Strengths</div>
                  <ul className="text-text">
                    {(selectedReport.strengths.length ? selectedReport.strengths : ["No strengths captured"]).map((item, idx) => (
                      <li key={idx}>- {item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-xs text-textMuted">Weaknesses</div>
                  <ul className="text-text">
                    {(selectedReport.weaknesses.length ? selectedReport.weaknesses : ["No weaknesses captured"]).map((item, idx) => (
                      <li key={idx}>- {item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-xs text-textMuted">Improvements</div>
                  <ul className="text-text">
                    {(selectedReport.improvements.length ? selectedReport.improvements : ["No improvements captured"]).map((item, idx) => (
                      <li key={idx}>- {item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-xs text-textMuted">Per Question Feedback</div>
                  <div className="max-h-72 space-y-3 overflow-auto pr-1">
                    {selectedReport.per_question.map((item, idx) => (
                      <div key={`${item.id}-${idx}`} className="rounded-lg border border-border bg-panelMuted p-3">
                        <div className="text-white">Q{idx + 1}. {item.question}</div>
                        <div className="mt-2 text-xs text-textMuted">Answer</div>
                        <div className="text-sm text-text">{item.answer || "No answer provided"}</div>
                        <div className="text-xs text-textMuted">Score: {item.score ?? 0}</div>
                        <div className="text-xs text-textMuted">Feedback: {item.feedback || "N/A"}</div>
                      </div>
                    ))}
                    {!selectedReport.per_question.length && (
                      <div className="text-xs text-textMuted">No per-question details available.</div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};
