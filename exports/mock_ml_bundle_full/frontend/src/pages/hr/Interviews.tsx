import { useEffect, useState } from "react";

import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch } from "../../lib/api";

type Interview = {
  id: number;
  candidate_user_id: number;
  job_id: number | null;
  type: string;
  status: string;
  overall_score: number | null;
  confidence_score: number | null;
  report: any;
  recording_url: string | null;
  created_at: string;
};

export const HrInterviews = () => {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [selected, setSelected] = useState<Interview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<{ items: Interview[] }>("/api/hr/interviews")
      .then((data) => setInterviews(data.items))
      .catch((err) => setError((err as Error).message));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Interview Reports"
        subtitle="Open an interview to review scoring, confidence, and full report JSON."
      />
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="space-y-3">
          <div className="text-lg font-semibold text-white">Interview Reports</div>
          {error && <p className="text-danger">{error}</p>}
          {interviews.length === 0 && (
            <EmptyState title="No interviews yet" description="Interview reports will appear here." />
          )}
          {interviews.map((interview) => (
            <button
              key={interview.id}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                selected?.id === interview.id ? "border-accent bg-panelMuted" : "border-border"
              }`}
              onClick={() => setSelected(interview)}
            >
              <div className="font-semibold text-white">Interview #{interview.id}</div>
              <div className="text-xs text-textMuted">
                {interview.type.toUpperCase()} · {interview.status}
              </div>
            </button>
          ))}
        </Card>

        <Card className="space-y-4">
          {!selected && <div className="text-textMuted">Select an interview to view details.</div>}
          {selected && (
            <>
              <div className="text-xl font-semibold text-white">Interview #{selected.id}</div>
              <div className="grid gap-2 text-sm text-textMuted">
                <div>Status: {selected.status}</div>
                <div>Type: {selected.type}</div>
                <div>Overall Score: {selected.overall_score ?? "N/A"}</div>
                <div>Confidence Score: {selected.confidence_score ?? "N/A"}</div>
                <div>Recording URL: {selected.recording_url ?? "Not available"}</div>
              </div>
              <div className="rounded-md border border-border bg-panelMuted p-3 text-xs text-textMuted">
                <div className="text-white">Report JSON</div>
                <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap text-text">
                  {JSON.stringify(selected.report, null, 2)}
                </pre>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};
