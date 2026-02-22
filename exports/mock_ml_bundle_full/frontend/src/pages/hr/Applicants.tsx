import { useEffect, useState } from "react";
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
    overall_score: number | null;
    confidence_score: number | null;
    status: string | null;
    recording_url: string | null;
  };
  mock_interview: {
    overall_score: number | null;
    confidence_score: number | null;
    status: string | null;
  };
};

export const HrApplicants = () => {
  const { jobId } = useParams();
  const [items, setItems] = useState<ApplicantItem[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Applicants"
        subtitle="Review candidate eligibility, interview scores, and take action."
      />
      {error && <p className="text-danger">{error}</p>}
      {items.length === 0 && (
        <EmptyState title="No applicants yet" description="Applications will appear as candidates apply." />
      )}
      <div className="grid gap-4">
        {items.map((item) => (
          <Card key={item.application.id} className="space-y-3">
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
              <div>
                AI Interview: {item.ai_interview.status || "pending"} · Score{" "}
                {item.ai_interview.overall_score ?? "N/A"}
              </div>
              <div>
                Mock Interview: {item.mock_interview.status || "N/A"} · Score{" "}
                {item.mock_interview.overall_score ?? "N/A"}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => updateStatus(item.application.id, "shortlisted")}>
                Shortlist
              </Button>
              <Button variant="danger" onClick={() => updateStatus(item.application.id, "rejected")}>
                Reject
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
