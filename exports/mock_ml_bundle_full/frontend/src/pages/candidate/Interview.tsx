import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { InterviewSession } from "../../components/InterviewSession";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch } from "../../lib/api";

type InterviewDetail = {
  interview: {
    id: number;
    status: string;
  };
};

export const CandidateInterview = () => {
  const { applicationId } = useParams();
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!applicationId) return;
    apiFetch<InterviewDetail>(`/api/candidate/interviews/by-application/${applicationId}`)
      .then((data) => setInterviewId(data.interview.id))
      .catch((err) => setError((err as Error).message));
  }, [applicationId]);

  if (error) {
    return <div className="text-danger">{error}</div>;
  }

  if (!interviewId) {
    return <div className="text-textMuted">Loading interview session...</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Interview Session"
        subtitle="Answer role-specific questions tailored to your resume and the job description."
      />
      <InterviewSession interviewId={interviewId} />
    </div>
  );
};
