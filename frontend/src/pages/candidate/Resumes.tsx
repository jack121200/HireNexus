import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { Input } from "../../components/Input";
import { Select } from "../../components/Select";
import { Textarea } from "../../components/Textarea";
import { apiFetch, apiUpload } from "../../lib/api";

type Resume = {
  id: number;
  file_name: string;
  file_type: string;
  is_primary: boolean;
  extracted_skills: string[];
  estimated_experience_years: number | null;
  education_level: string | null;
  created_at: string;
};

type ResumeUploadResponse = { resume: Resume };

type Eligibility = {
  eligibility_percentage: number;
  skill_match_percentage: number;
  experience_match_percentage: number;
  education_match_percentage: number;
  missing_skills: string[];
  suggestions: string[];
  required_skills: string[];
};

export const CandidateResumes = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [jdText, setJdText] = useState("");
  const [analysis, setAnalysis] = useState<Eligibility | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadResumes = () => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (data.length && !selectedResumeId) {
          setSelectedResumeId(data[0].id);
        }
      })
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => {
    loadResumes();
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await apiUpload<ResumeUploadResponse>("/api/candidate/resumes", formData);
      setFile(null);
      loadResumes();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedResumeId) return;
    setError(null);
    try {
      const response = await apiFetch<{ eligibility: Eligibility }>(`/api/candidate/resumes/${selectedResumeId}/analyze`, {
        method: "POST",
        body: JSON.stringify({
          jd_text: jdText,
          required_skills: [],
          minimum_experience_years: 0,
          education_requirement: null,
        }),
      });
      setAnalysis(response.eligibility);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDownload = async () => {
    if (!selectedResumeId) return;
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/api/candidate/resumes/${selectedResumeId}/download`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("hn_token") ?? ""}`,
        },
      });
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = resumes.find((item) => item.id === selectedResumeId)?.file_name || "resume";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const setPrimary = async (resumeId: number) => {
    try {
      await apiFetch(`/api/candidate/resumes/${resumeId}/set-primary`, { method: "POST" });
      loadResumes();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const matchedSkills = useMemo(() => {
    if (!analysis) return [];
    const missing = new Set(analysis.missing_skills);
    return analysis.required_skills.filter((skill) => !missing.has(skill));
  }, [analysis]);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Candidate Suite"
        title="Resume Intelligence"
        subtitle="Upload your resume, analyze skill gaps, and get actionable improvements aligned to real jobs."
      />
      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Card variant="glass" className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Upload Resume</h2>
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <Input
              label="Select File"
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            <Button onClick={handleUpload} disabled={!file}>
              Upload
            </Button>
          </div>
          <div className="rounded-xl border border-border/70 bg-panelMuted/70 p-3 text-xs text-textMuted">
            Supported formats: PDF, DOCX, TXT. Files are stored securely and used for AI-powered matching.
          </div>
        </Card>

        <Card variant="muted" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">My Resumes</h2>
            <Button variant="secondary" onClick={handleDownload} disabled={!selectedResumeId}>
              Download
            </Button>
          </div>
          {resumes.length === 0 && (
            <EmptyState title="No resumes yet" description="Upload a resume to unlock eligibility scoring." />
          )}
          {resumes.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {resumes.map((resume) => (
                <div key={resume.id} className="rounded-xl border border-border/70 bg-panelMuted/70 p-4 text-sm">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-white">{resume.file_name}</div>
                      <div className="text-xs text-textMuted">{resume.file_type}</div>
                    </div>
                    {resume.is_primary ? (
                      <span className="rounded-full border border-accent px-2 py-1 text-[10px] uppercase text-accent">
                        Primary
                      </span>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => setPrimary(resume.id)}>
                        Set Primary
                      </Button>
                    )}
                  </div>
                  <div className="mt-3 grid gap-1 text-xs text-textMuted">
                    <div>Experience: {resume.estimated_experience_years ?? "N/A"} yrs</div>
                    <div>Education: {resume.education_level ?? "N/A"}</div>
                    <div>
                      Skills: {resume.extracted_skills.slice(0, 6).join(", ") || "None"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card variant="glass" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white">Resume vs JD Analysis</h2>
            <p className="text-sm text-textMuted">Paste a job description to see what you are missing and how to improve.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleAnalyze} disabled={!selectedResumeId || !jdText.trim()}>
              Analyze
            </Button>
            <Button variant="secondary" onClick={() => setShowSuggestions((prev) => !prev)}>
              {showSuggestions ? "Hide Suggestions" : "Show Suggestions"}
            </Button>
            <Button variant="ghost" onClick={() => setJdText("")}>Clear JD</Button>
          </div>
        </div>
        <Select
          label="Resume"
          value={selectedResumeId ?? undefined}
          onChange={(event) => setSelectedResumeId(Number(event.target.value))}
        >
          {resumes.map((resume) => (
            <option key={resume.id} value={resume.id}>
              {resume.file_name}
            </option>
          ))}
        </Select>
        <Textarea
          label="Paste Job Description"
          value={jdText}
          onChange={(event) => setJdText(event.target.value)}
        />

        {analysis && (
          <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
            <div className="rounded-xl border border-border/70 bg-panelMuted/70 p-4">
              <div className="text-sm font-semibold text-white">Overall Eligibility</div>
              <div className="mt-2 text-3xl font-semibold text-white">
                {analysis.eligibility_percentage.toFixed(1)}%
              </div>
              <div className="mt-3 grid gap-2 text-xs text-textMuted">
                <div>Skill Match: {analysis.skill_match_percentage.toFixed(1)}%</div>
                <div>Experience Match: {analysis.experience_match_percentage.toFixed(1)}%</div>
                <div>Education Match: {analysis.education_match_percentage.toFixed(1)}%</div>
              </div>
            </div>
            <div className="rounded-xl border border-border/70 bg-panelMuted/70 p-4">
              <div className="text-sm font-semibold text-white">What you are already doing well</div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                {matchedSkills.length ? (
                  matchedSkills.map((skill) => (
                    <span key={skill} className="rounded-full border border-border px-2 py-1 text-textMuted">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-textMuted">No strong matches yet. Consider adding targeted skills.</span>
                )}
              </div>
            </div>
          </div>
        )}

        {analysis && (
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
            <div className="rounded-xl border border-border/70 bg-panelMuted/70 p-4">
              <div className="text-sm font-semibold text-white">What is missing</div>
              <div className="mt-2 text-xs text-textMuted">
                {analysis.missing_skills.length
                  ? analysis.missing_skills.join(", ")
                  : "No major skill gaps detected."}
              </div>
            </div>
            <div className="rounded-xl border border-border/70 bg-panelMuted/70 p-4">
              <div className="text-sm font-semibold text-white">How to improve (examples)</div>
              <div className="mt-2 space-y-2 text-xs text-textMuted">
                {showSuggestions && analysis.suggestions.length > 0 ? (
                  analysis.suggestions.map((item) => <div key={item}>- {item}</div>)
                ) : (
                  <div>Enable suggestions to view tailored improvements.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
