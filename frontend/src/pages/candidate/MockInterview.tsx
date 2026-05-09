import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { PageHeader } from "../../components/PageHeader";
import { InterviewSession } from "../../components/InterviewSession";
import { Input } from "../../components/Input";
import { Select } from "../../components/Select";
import { Textarea } from "../../components/Textarea";
import { apiFetch } from "../../lib/api";

type Resume = {
  id: number;
  file_name: string;
};

type InterviewResponse = {
  interview: { id: number };
};

const ROLE_PRESETS: { label: string; role: string; jd: string }[] = [
  {
    label: "🖥️ Backend Eng",
    role: "Backend Engineer",
    jd: "We are looking for a Backend Engineer with 3+ years building scalable REST APIs using Python/FastAPI or Node.js. Must have strong SQL (PostgreSQL/MySQL), Redis, Docker. Bonus: Kubernetes, AWS, GraphQL.",
  },
  {
    label: "⚛️ Frontend Eng",
    role: "Frontend Engineer",
    jd: "We need a Frontend Engineer proficient in React, TypeScript, and Tailwind CSS. Should understand state management (Zustand/Redux), performance optimization, and have experience with Vite or Next.js.",
  },
  {
    label: "🤖 ML Engineer",
    role: "Machine Learning Engineer",
    jd: "ML Engineer role — Python, PyTorch/TensorFlow, model training and fine-tuning, MLOps (experiment tracking, deployment), REST APIs for serving models. RAG/LLM experience is a strong plus.",
  },
  {
    label: "☁️ DevOps",
    role: "DevOps Engineer",
    jd: "DevOps Engineer with 2+ years experience in CI/CD pipelines (GitHub Actions, Jenkins), Docker, Kubernetes, AWS/GCP, Terraform, monitoring (Prometheus, Grafana).",
  },
];

export const MockInterview = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [role, setRole] = useState("");
  const [years, setYears] = useState("2");
  const [jdText, setJdText] = useState("");
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (data.length) setResumeId(data[0].id);
      })
      .catch((err) => setError((err as Error).message));
  }, []);

  const applyPreset = (preset: (typeof ROLE_PRESETS)[number]) => {
    setRole(preset.role);
    setJdText(preset.jd);
  };

  const startMockInterview = async () => {
    setError(null);
    try {
      const response = await apiFetch<InterviewResponse>("/api/candidate/interviews/mock", {
        method: "POST",
        body: JSON.stringify({
          role,
          years_experience: Number(years),
          resume_id: resumeId,
          jd_text: jdText,
        }),
      });
      setInterviewId(response.interview.id);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Candidate Suite"
        title="Mock Interview Studio"
        subtitle="Practice with an AI interviewer that adapts to your resume, experience, and job description."
      />
      {error && <p className="text-sm text-danger">{error}</p>}

      {!interviewId && (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          <Card variant="glass" className="space-y-5">
            <div>
              <div className="text-lg font-bold text-white">Interview Setup</div>
              <div className="text-xs text-textMuted mt-0.5">Fill manually or pick a quick preset below</div>
            </div>

            {/* Role presets */}
            <div className="space-y-2">
              <div className="text-[11px] uppercase tracking-wider text-textMuted">Quick Presets</div>
              <div className="flex flex-wrap gap-2">
                {ROLE_PRESETS.map((preset) => (
                  <button
                    key={preset.role}
                    onClick={() => applyPreset(preset)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${role === preset.role
                        ? "border-accent/60 bg-accent/15 text-accent"
                        : "border-border bg-panelMuted text-textMuted hover:border-accent/40 hover:text-white"
                      }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <Input label="Target Role" value={role} onChange={(e) => setRole(e.target.value)} />
            <Input
              label="Years of Experience"
              type="number"
              min={0}
              value={years}
              onChange={(e) => setYears(e.target.value)}
            />
            <Select
              label="Resume"
              value={resumeId ?? undefined}
              onChange={(e) => setResumeId(Number(e.target.value))}
            >
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.file_name}
                </option>
              ))}
            </Select>
            <Textarea label="Paste Job Description" value={jdText} onChange={(e) => setJdText(e.target.value)} />
            <Button onClick={startMockInterview} disabled={!role || !jdText}>
              🎙️ Start Mock Interview
            </Button>
          </Card>


          <Card variant="muted" className="space-y-4">
            <div className="text-lg font-semibold text-white">What to Expect</div>
            <div className="text-sm text-textMuted">
              Your questions are generated dynamically from your resume, the role, and the job description. The AI interviewer
              will respond instantly and adjust follow-up prompts based on your answers.
            </div>
            <div className="rounded-lg border border-border bg-panelMuted p-4 text-sm text-textMuted">
              <div className="text-xs uppercase text-textMuted">Interview flow</div>
              <ul className="mt-2 space-y-2">
                <li>• Natural greeting and context setting</li>
                <li>• Progressive questions from fundamentals to scenario deep-dives</li>
                <li>• Adaptive follow-ups based on your response quality</li>
                <li>• Detailed report with scores and ideal guidance</li>
              </ul>
            </div>
            <div className="rounded-lg border border-border bg-panelMuted p-4 text-xs text-textMuted">
              Tip: Use STAR format (Situation, Task, Action, Result) for crisp and confident answers.
            </div>
          </Card>
        </div>
      )}

      {interviewId && <InterviewSession interviewId={interviewId} />}
    </div>
  );
};
