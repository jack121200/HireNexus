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
  id: number; file_name: string; file_type: string; is_primary: boolean;
  extracted_skills: string[]; estimated_experience_years: number | null;
  education_level: string | null; created_at: string;
};

type Eligibility = {
  eligibility_percentage: number; skill_match_percentage: number;
  experience_match_percentage: number; education_match_percentage: number;
  missing_skills: string[]; suggestions: string[]; required_skills: string[];
};

export const CandidateResumes = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [jdText, setJdText] = useState("");
  const [analysis, setAnalysis] = useState<Eligibility | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadResumes = () => {
    apiFetch<Resume[]>("/api/candidate/resumes")
      .then((data) => {
        setResumes(data);
        if (data.length && !selectedResumeId) setSelectedResumeId(data[0].id);
      })
      .catch((err) => setError((err as Error).message));
  };

  useEffect(() => { loadResumes(); }, []);

  const handleUpload = async () => {
    if (!file) return;
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await apiUpload<{ resume: Resume }>("/api/candidate/resumes", formData);
      setFile(null);
      loadResumes();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedResumeId || !jdText.trim()) return;
    setError(null);
    setIsAnalyzing(true);
    setAnalysis(null);
    
    // Simulate terminal delay for UI effect
    await new Promise(r => setTimeout(r, 800));
    
    try {
      const response = await apiFetch<{ eligibility: Eligibility }>(`/api/candidate/resumes/${selectedResumeId}/analyze`, {
        method: "POST",
        body: JSON.stringify({ jd_text: jdText, required_skills: [], minimum_experience_years: 0, education_requirement: null }),
      });
      setAnalysis(response.eligibility);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const setPrimary = async (resumeId: number) => {
    try {
      await apiFetch(`/api/candidate/resumes/${resumeId}/set-primary`, { method: "POST" });
      loadResumes();
    } catch (err) { setError((err as Error).message); }
  };

  const matchedSkills = useMemo(() => {
    if (!analysis) return [];
    const missing = new Set(analysis.missing_skills);
    return analysis.required_skills.filter((skill) => !missing.has(skill));
  }, [analysis]);

  return (
    <div className="space-y-8 page-enter pb-20">
      <PageHeader
        kicker="Intelligence Hub"
        title="Resume Vault"
        subtitle="Manage your profiles, run real-time JD parsing, and prepare for interviews."
      />
      {error && <div className="p-3 text-sm text-danger border border-danger/30 bg-danger/10 rounded-lg">{error}</div>}

      <div className="grid lg:grid-cols-[380px_1fr] gap-6 items-start">
        {/* Left Column: Upload */}
        <Card variant="surface" className="sticky top-24 space-y-6 !p-6">
          <div>
            <h2 className="text-lg font-bold text-text">New Upload</h2>
            <p className="text-xs text-textDim mt-1">Accepts PDF, DOCX, TXT. AI parsing runs securely.</p>
          </div>
          
          <div className="border border-dashed border-border hover:border-accent/40 bg-panelMuted/30 transition-colors rounded-xl p-6 text-center group cursor-pointer relative">
            <input 
              type="file" 
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
              onChange={(e) => setFile(e.target.files?.[0] || null)} 
              title="Click to select file"
            />
            <div className="text-2xl mb-2 grayscale group-hover:grayscale-0 transition-all">📄</div>
            <div className="text-sm font-medium text-text group-hover:text-accent transition-colors">
              {file ? file.name : "Click to select or drag file"}
            </div>
            {file && <div className="text-[10px] text-textDim mt-1">{(file.size / 1024).toFixed(0)} KB ready</div>}
          </div>
          
          <Button className="w-full" onClick={handleUpload} disabled={!file}>
            Process Document
          </Button>

          {/* List of resumes below upload in the sidebar */}
          <div className="pt-6 border-t border-border mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-4">Your Vault</h3>
            {resumes.length === 0 ? (
              <div className="text-sm text-textDim italic">No documents yet.</div>
            ) : (
              <div className="space-y-3">
                {resumes.map(r => (
                  <div key={r.id} className={`p-3 rounded-lg border ${selectedResumeId === r.id ? "border-accent bg-accent/5 ring-1 ring-accent/20" : "border-border bg-panelMuted"} transition-all cursor-pointer`} onClick={() => setSelectedResumeId(r.id)}>
                    <div className="flex justify-between items-start">
                      <div className="font-medium text-sm text-text truncate pr-2">{r.file_name}</div>
                      {r.is_primary && <span className="bg-accent text-white text-[9px] uppercase px-1.5 py-0.5 rounded uppercase font-bold tracking-widest leading-none">Primary</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-[11px] text-textDim">
                      <span>{r.estimated_experience_years ?? 0} yrs exp</span>
                      <span>·</span>
                      <span className="uppercase">{r.file_type.split("/").pop() || "TXT"}</span>
                    </div>
                    {!r.is_primary && (
                      <div className="mt-2 flex justify-end">
                        <span onClick={(e) => {e.stopPropagation(); setPrimary(r.id);}} className="text-[10px] text-textMuted hover:text-accent transition-colors cursor-pointer hover:underline">Mark Primary</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Right Column: AI Analysis Terminal */}
        <div className="space-y-6">
          <Card variant="surface" className="!p-0 overflow-hidden border border-border shadow-2xl">
            {/* Terminal Header */}
            <div className="px-4 py-3 bg-panelMuted border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-mono text-textMuted">
                <span className="text-accent">~/hirenexus/ai</span>
                <span>$ analyzer --jd-mode run</span>
              </div>
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-danger/50" />
                <div className="w-2.5 h-2.5 rounded-full bg-warning/50" />
                <div className="w-2.5 h-2.5 rounded-full bg-success/50" />
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div className="text-sm font-medium text-text mb-2">Paste Job Description</div>
              <Textarea
                className="font-mono text-xs bg-black text-green-500/80 border-border/50 focus:border-green-500/50 resize-y min-h-[160px]"
                placeholder="[JD Output Stream Waiting...]"
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
              />
              <div className="flex justify-end pt-2">
                <Button 
                  onClick={handleAnalyze} 
                  disabled={!selectedResumeId || !jdText.trim() || isAnalyzing}
                  className="bg-white text-black hover:bg-white/90 font-mono tracking-tight"
                >
                  {isAnalyzing ? "Executing Matrix..." : "[ Run Analysis ]"}
                </Button>
              </div>
            </div>

            {/* Analysis Results Display */}
            {isAnalyzing && (
              <div className="px-6 pb-6 pt-2 font-mono text-xs text-textDim space-y-1">
                <div className="text-green-500">{">"} Init vector embeddings... OK</div>
                <div className="text-green-500">{">"} Tokenizing JD specs... OK</div>
                <div className="animate-pulse">{">"} Computing semantic overlap score...</div>
              </div>
            )}

            {analysis && !isAnalyzing && (
              <div className="border-t border-border bg-black/40 p-6 space-y-8 animate-fadeIn">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <h3 className="text-lg font-bold text-white tracking-tight">Eligibility Score</h3>
                    <p className="text-sm text-textDim">Measured against structural JD requirements</p>
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className={`text-6xl font-black tabular-nums tracking-tighter ${analysis.eligibility_percentage >= 70 ? "text-green-500" : analysis.eligibility_percentage >= 40 ? "text-warning" : "text-danger"}`}>
                      {analysis.eligibility_percentage.toFixed(0)}
                    </span>
                    <span className="text-2xl text-textDim font-light">%</span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-px bg-border/50 border border-border/50 rounded-lg overflow-hidden">
                  <div className="bg-panelMuted/80 p-4 text-center">
                    <div className="text-[10px] uppercase text-textDim tracking-widest mb-1">Skills</div>
                    <div className="font-mono text-lg text-white">{analysis.skill_match_percentage.toFixed(0)}%</div>
                  </div>
                  <div className="bg-panelMuted/80 p-4 text-center">
                    <div className="text-[10px] uppercase text-textDim tracking-widest mb-1">Experience</div>
                    <div className="font-mono text-lg text-white">{analysis.experience_match_percentage.toFixed(0)}%</div>
                  </div>
                  <div className="bg-panelMuted/80 p-4 text-center">
                    <div className="text-[10px] uppercase text-textDim tracking-widest mb-1">Education</div>
                    <div className="font-mono text-lg text-white">{analysis.education_match_percentage.toFixed(0)}%</div>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <h4 className="text-xs uppercase text-textDim font-semibold flex items-center gap-2">
                       <span className="w-2 h-2 rounded-full bg-green-500"></span> Current Matches
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {matchedSkills.length ? matchedSkills.map(s => (
                        <span key={s} className="px-2 py-1 bg-green-500/10 border border-green-500/20 text-green-500 rounded text-xs">✓ {s}</span>
                      )) : <span className="text-xs text-textDim italic">None strictly matched</span>}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <h4 className="text-xs uppercase text-textDim font-semibold flex items-center gap-2">
                       <span className="w-2 h-2 rounded-full bg-danger"></span> Missing Criticals
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {analysis.missing_skills.length ? analysis.missing_skills.map(s => (
                        <span key={s} className="px-2 py-1 bg-danger/10 border border-danger/20 text-danger rounded text-xs">! {s}</span>
                      )) : <span className="text-xs text-textDim italic">Nothing missing</span>}
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-4 border-t border-border/50">
                  <h4 className="text-xs uppercase text-textDim font-semibold">AI Actionable Suggestions</h4>
                  <ul className="space-y-2">
                    {analysis.suggestions.map((s, i) => (
                      <li key={i} className="text-sm text-text leading-relaxed flex items-start gap-2">
                        <span className="text-accent mt-0.5">↳</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
