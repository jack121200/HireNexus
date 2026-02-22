import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { Card } from "../../components/Card";
import { Button } from "../../components/Button";
import { apiFetch } from "../../lib/api";

type InterviewDetail = {
  interview: {
    id: number;
    type: string;
    status: string;
    overall_score: number | null;
    confidence_score: number | null;
    report: any;
    transcript: string | null;
    recording_url: string | null;
  };
};

export const InterviewReport = () => {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<InterviewDetail["interview"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    if (!interviewId) return;
    setLoading(true);
    apiFetch<InterviewDetail>(`/api/candidate/interviews/${interviewId}`)
      .then((res) => setData(res.interview))
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [interviewId]);

  if (loading) {
    return <div className="text-textMuted">Loading interview report...</div>;
  }

  if (error || !data) {
    return <div className="text-danger">{error ?? "Unable to load report"}</div>;
  }

  const scoring = data.report?.scoring || {};
  const perQuestion = scoring.per_question || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-lg font-semibold text-white">Interview Report</div>
          <div className="text-xs text-textMuted">Session #{data.id} ? {data.type.toUpperCase()}</div>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => navigate(-1)}>Back</Button>
          <Button
            variant="secondary"
            onClick={() => window.open(`${baseUrl}/api/candidate/interviews/${data.id}/report.pdf`, "_blank")}
          >
            Download PDF
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-2">
          <div className="text-xs text-textMuted">Overall Score</div>
          <div className="text-3xl font-semibold text-white">{data.overall_score?.toFixed(1) ?? "--"}%</div>
          <div className="h-2 w-full rounded-full bg-border/60">
            <div className="h-2 rounded-full bg-accent" style={{ width: `${data.overall_score ?? 0}%` }} />
          </div>
        </Card>
        <Card className="space-y-2">
          <div className="text-xs text-textMuted">Confidence Score</div>
          <div className="text-3xl font-semibold text-white">{data.confidence_score?.toFixed(1) ?? "--"}%</div>
          <div className="h-2 w-full rounded-full bg-border/60">
            <div className="h-2 rounded-full bg-success" style={{ width: `${data.confidence_score ?? 0}%` }} />
          </div>
        </Card>
      </div>

      <Card className="space-y-3">
        <div className="text-sm text-textMuted">Summary</div>
        <div className="text-sm text-text">{scoring.feedback_summary ?? "Evaluation complete"}</div>
        <div className="grid gap-4 md:grid-cols-3 text-sm">
          <div>
            <div className="text-xs text-textMuted">Strengths</div>
            <ul className="mt-2 space-y-1 text-text">
              {(scoring.strengths || ["No strengths captured yet"]).map((item: string, idx: number) => (
                <li key={idx}>? {item}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs text-textMuted">Weaknesses</div>
            <ul className="mt-2 space-y-1 text-text">
              {(scoring.weaknesses || ["No weaknesses captured yet"]).map((item: string, idx: number) => (
                <li key={idx}>? {item}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs text-textMuted">Improvements</div>
            <ul className="mt-2 space-y-1 text-text">
              {(scoring.improvements || ["No improvements captured yet"]).map((item: string, idx: number) => (
                <li key={idx}>? {item}</li>
              ))}
            </ul>
          </div>
        </div>
      </Card>

      <Card className="space-y-4">
        <div className="text-sm text-textMuted">Per Question Breakdown</div>
        <div className="space-y-4">
          {perQuestion.length === 0 && <div className="text-textMuted">No questions captured.</div>}
          {perQuestion.map((item: any, idx: number) => (
            <div key={`${item.id}-${idx}`} className="rounded-xl border border-border bg-panelMuted p-4">
              <div className="text-sm text-white">Q{idx + 1}. {item.question}</div>
              <div className="mt-2 text-xs text-textMuted">Answer</div>
              <div className="text-sm text-text">{item.answer || "(No answer)"}</div>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-textMuted">
                <span className="rounded-full border border-border bg-panel px-3 py-1">Score: {item.score ?? 0}%</span>
                <span className="rounded-full border border-border bg-panel px-3 py-1">Difficulty: {item.difficulty}</span>
                <span className="rounded-full border border-border bg-panel px-3 py-1">Category: {item.category}</span>
              </div>
              <div className="mt-3 text-xs text-textMuted">Feedback</div>
              <div className="text-sm text-text">{item.feedback || "No feedback"}</div>
              <div className="mt-3 text-xs text-textMuted">Ideal Guidance</div>
              <div className="text-sm text-text">
                {(item.rubric_points || []).length ? (item.rubric_points || []).join(" ? ") : "No rubric provided"}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
