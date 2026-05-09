import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../../components/PageHeader";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { apiFetch } from "../../lib/api";

type InterviewItem = {
  id: number;
  type: "ai" | "mock";
  status: string;
  overall_score: number | null;
  created_at: string;
  completed_at: string | null;
};

type InterviewListResponse = {
  items: InterviewItem[];
};

const statusTone = (s: string): "success" | "warning" | "danger" | "default" => {
  if (s === "completed") return "success";
  if (s === "in_progress") return "warning";
  if (s === "failed") return "danger";
  return "default";
};

export const CandidateInterviews = () => {
  const [items, setItems] = useState<InterviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<InterviewListResponse>("/api/candidate/interviews")
      .then((res) => setItems(res.items))
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Candidate Suite"
        title="My Interviews"
        subtitle="View your AI and mock interview history, scores, and detailed reports."
        actions={
          <Link to="/candidate/mock-interview">
            <Button size="sm">🎙️ New Mock Interview</Button>
          </Link>
        }
      />

      {error && <p className="text-sm text-danger">⚠ {error}</p>}

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl shimmer" />
          ))}
        </div>
      )}

      {!loading && items.length === 0 && (
        <Card className="text-center py-12 space-y-3">
          <div className="text-3xl">🎙️</div>
          <div className="text-text font-semibold">No interviews yet</div>
          <p className="text-sm text-textMuted">
            Apply for a job to trigger an AI interview, or start a mock session to practice.
          </p>
          <Link to="/candidate/mock-interview">
            <Button className="mt-2">Start Mock Interview</Button>
          </Link>
        </Card>
      )}

      {!loading && items.length > 0 && (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-xl border border-border bg-panel px-5 py-4 gap-4 flex-wrap"
            >
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 border border-accent/20 text-lg">
                  {item.type === "ai" ? "🤖" : "🧑‍💻"}
                </div>
                <div>
                  <div className="text-sm font-semibold text-text">
                    {item.type === "ai" ? "AI Interview" : "Mock Interview"}
                  </div>
                  <div className="text-xs text-textMuted mt-0.5">
                    {new Date(item.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 flex-wrap">
                <Badge tone={statusTone(item.status)}>
                  {item.status.replace("_", " ")}
                </Badge>

                {item.overall_score !== null && (
                  <div className="text-sm font-bold text-accent">
                    {item.overall_score.toFixed(1)}<span className="text-textMuted font-normal">/100</span>
                  </div>
                )}

                {item.status === "completed" && (
                  <Link to={`/candidate/interview/${item.id}/report`}>
                    <Button variant="secondary" size="sm">View Report</Button>
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
