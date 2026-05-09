import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiFetch } from "../../lib/api";

type QuestionScore = {
  id: string;
  question: string;
  answer: string;
  score: number;
  difficulty: string;
  category: string;
  feedback: string;
  rubric_points: string[];
};

type Scoring = {
  feedback_summary: string;
  strengths: string[];
  weaknesses: string[];
  improvements: string[];
  per_question: QuestionScore[];
};

type InterviewData = {
  id: number;
  type: string;
  status: string;
  overall_score: number | null;
  confidence_score: number | null;
  report: { scoring?: Scoring } | null;
  transcript: string | null;
};

type InterviewDetail = { interview: InterviewData };

const ScoreRing = ({ score, label, color }: { score: number | null; label: string; color: string }) => {
  const pct = score ?? 0;
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative h-24 w-24">
        <svg className="rotate-[-90deg]" width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r={r} stroke="rgba(255,255,255,0.06)" strokeWidth="8" fill="none" />
          <circle
            cx="48" cy="48" r={r}
            stroke={color} strokeWidth="8" fill="none"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold text-white">{score !== null ? `${pct.toFixed(0)}` : "—"}</span>
        </div>
      </div>
      <span className="text-xs text-white/50 font-medium uppercase tracking-wider">{label}</span>
    </div>
  );
};

const ScoreBar = ({ score }: { score: number }) => {
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div className="h-1.5 w-full rounded-full bg-white/5">
      <div className="h-1.5 rounded-full transition-all duration-700" style={{ width: `${score}%`, background: color }} />
    </div>
  );
};

const categoryIcon: Record<string, string> = {
  technical: "⚙️", behavioral: "🤝", communication: "💬",
  leadership: "🏆", problem_solving: "🧠", default: "🎯",
};

export const InterviewReport = () => {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<InterviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "questions" | "transcript">("overview");
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    if (!interviewId) return;
    apiFetch<InterviewDetail>(`/api/candidate/interviews/${interviewId}`)
      .then((res) => setData(res.interview))
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [interviewId]);

  if (loading) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 rounded-full border-2 border-indigo-500/30 border-t-indigo-400 animate-spin" />
        <div className="text-sm text-white/40">Loading report…</div>
      </div>
    </div>
  );

  if (error || !data) return (
    <div className="min-h-[40vh] flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="text-3xl">⚠️</div>
        <div className="text-sm text-red-400">{error ?? "Unable to load report"}</div>
        <button onClick={() => navigate(-1)} className="text-xs text-white/40 hover:text-white underline">Go back</button>
      </div>
    </div>
  );

  const scoring = data.report?.scoring;
  const perQuestion = scoring?.per_question ?? [];
  const overall = data.overall_score ?? 0;
  const confidence = data.confidence_score ?? 0;

  const grade = overall >= 90 ? { label: "Excellent", color: "#22c55e" }
    : overall >= 75 ? { label: "Good", color: "#6366f1" }
    : overall >= 60 ? { label: "Average", color: "#f59e0b" }
    : { label: "Needs Work", color: "#ef4444" };

  return (
    <div
      className="min-h-screen"
      style={{ background: "radial-gradient(ellipse 80% 40% at 50% 0%, #0f1a36 0%, #05080f 70%)" }}
    >
      {/* Header */}
      <div className="border-b border-white/5 px-6 py-5 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/candidate/interviews")}
            className="text-white/40 hover:text-white text-sm flex items-center gap-1 transition-colors"
          >
            ← Interviews
          </button>
          <span className="text-white/20">/</span>
          <span className="text-sm text-white font-semibold">Report #{data.id}</span>
          <span className="text-[11px] px-2 py-0.5 rounded-full border border-white/10 bg-white/5 text-white/50 capitalize">
            {data.type} interview
          </span>
        </div>
        <button
          onClick={() => window.open(`${baseUrl}/api/candidate/interviews/${data.id}/report.pdf`, "_blank")}
          className="text-xs font-medium px-4 py-2 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 transition-colors"
        >
          ↓ Download PDF
        </button>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Score hero */}
        <div
          className="rounded-2xl border border-white/8 p-8"
          style={{ background: "linear-gradient(145deg, rgba(99,102,241,0.08) 0%, rgba(10,14,30,0.9) 100%)" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-8">
            <div className="flex items-center gap-8">
              <ScoreRing score={data.overall_score} label="Overall" color={grade.color} />
              <ScoreRing score={data.confidence_score} label="Confidence" color="#6366f1" />
            </div>
            <div className="flex-1 min-w-[200px]">
              <div
                className="inline-block px-3 py-1 rounded-full text-xs font-bold mb-3"
                style={{ background: `${grade.color}20`, color: grade.color, border: `1px solid ${grade.color}40` }}
              >
                {grade.label}
              </div>
              <p className="text-sm text-white/60 leading-relaxed">
                {scoring?.feedback_summary ?? "Your interview has been scored. Review each section below for detailed feedback."}
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 rounded-xl bg-white/5 border border-white/5 w-fit">
          {(["overview", "questions", "transcript"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all"
              style={activeTab === tab
                ? { background: "rgba(99,102,241,0.3)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)" }
                : { color: "rgba(255,255,255,0.4)" }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="grid gap-4 md:grid-cols-3">
            {/* Strengths */}
            <div className="rounded-2xl border border-green-500/15 bg-green-500/5 p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-6 w-6 rounded-full bg-green-500/20 flex items-center justify-center text-xs">✓</div>
                <span className="text-sm font-semibold text-green-400">Strengths</span>
              </div>
              <ul className="space-y-2">
                {(scoring?.strengths ?? ["No strengths captured yet"]).map((s, i) => (
                  <li key={i} className="text-sm text-white/70 flex gap-2">
                    <span className="text-green-500 mt-0.5 flex-shrink-0">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
            {/* Weaknesses */}
            <div className="rounded-2xl border border-red-500/15 bg-red-500/5 p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-6 w-6 rounded-full bg-red-500/20 flex items-center justify-center text-xs">✗</div>
                <span className="text-sm font-semibold text-red-400">Areas to Improve</span>
              </div>
              <ul className="space-y-2">
                {(scoring?.weaknesses ?? ["No weaknesses captured yet"]).map((w, i) => (
                  <li key={i} className="text-sm text-white/70 flex gap-2">
                    <span className="text-red-400 mt-0.5 flex-shrink-0">•</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
            {/* Improvements */}
            <div className="rounded-2xl border border-amber-500/15 bg-amber-500/5 p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-6 w-6 rounded-full bg-amber-500/20 flex items-center justify-center text-xs">↑</div>
                <span className="text-sm font-semibold text-amber-400">Next Steps</span>
              </div>
              <ul className="space-y-2">
                {(scoring?.improvements ?? ["No improvements captured yet"]).map((imp, i) => (
                  <li key={i} className="text-sm text-white/70 flex gap-2">
                    <span className="text-amber-400 mt-0.5 flex-shrink-0">•</span>
                    {imp}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* QUESTIONS TAB */}
        {activeTab === "questions" && (
          <div className="space-y-4">
            {perQuestion.length === 0 && (
              <div className="rounded-2xl border border-white/5 bg-white/3 p-8 text-center text-white/40 text-sm">
                No per-question data yet. This appears once the scorer has processed your transcript.
              </div>
            )}
            {perQuestion.map((q, i) => (
              <div key={i} className="rounded-2xl border border-white/6 bg-white/3 p-5 space-y-4">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex items-start gap-3">
                    <div className="h-7 w-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-300 flex-shrink-0">
                      {i + 1}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{q.question}</div>
                      <div className="flex gap-2 mt-1">
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/40 capitalize">
                          {categoryIcon[q.category] ?? categoryIcon.default} {q.category}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/40 capitalize">
                          {q.difficulty}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-2xl font-bold" style={{ color: q.score >= 80 ? "#22c55e" : q.score >= 60 ? "#f59e0b" : "#ef4444" }}>
                    {q.score}<span className="text-sm text-white/30">/100</span>
                  </div>
                </div>

                <ScoreBar score={q.score} />

                {q.answer && (
                  <div>
                    <div className="text-xs text-white/30 mb-1 uppercase tracking-wider">Your Answer</div>
                    <div className="text-sm text-white/60 bg-white/3 rounded-lg p-3 border border-white/5">{q.answer}</div>
                  </div>
                )}

                {q.feedback && (
                  <div>
                    <div className="text-xs text-white/30 mb-1 uppercase tracking-wider">AI Feedback</div>
                    <div className="text-sm text-indigo-200/80">{q.feedback}</div>
                  </div>
                )}

                {q.rubric_points?.length > 0 && (
                  <div>
                    <div className="text-xs text-white/30 mb-2 uppercase tracking-wider">Ideal Answer Points</div>
                    <div className="flex flex-wrap gap-2">
                      {q.rubric_points.map((pt, j) => (
                        <span key={j} className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
                          {pt}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* TRANSCRIPT TAB */}
        {activeTab === "transcript" && (
          <div className="rounded-2xl border border-white/6 bg-white/3 p-5">
            {data.transcript ? (
              <pre className="text-sm text-white/60 whitespace-pre-wrap font-mono leading-relaxed">{data.transcript}</pre>
            ) : (
              <div className="text-center text-white/30 text-sm py-8">
                Transcript not available yet — it's processed after the call ends.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
