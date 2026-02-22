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
          <Card variant="glass" className="space-y-4">
            <div className="text-lg font-semibold text-white">Interview Setup</div>
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
              Start Mock Interview
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
