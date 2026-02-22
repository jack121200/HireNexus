import { useState } from "react";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { PageHeader } from "../../components/PageHeader";
import { Input } from "../../components/Input";
import { Textarea } from "../../components/Textarea";
import { apiFetch } from "../../lib/api";

type JobCreateResponse = {
  job: { id: number; title: string };
};

export const HrPostJob = () => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [responsibilities, setResponsibilities] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [minExperience, setMinExperience] = useState("1");
  const [education, setEducation] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("Full-time");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setStatus(null);
    setError(null);
    try {
      const response = await apiFetch<JobCreateResponse>("/api/hr/jobs", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          responsibilities,
          required_skills: requiredSkills.split(",").map((s) => s.trim()).filter(Boolean),
          minimum_experience_years: Number(minExperience),
          education_requirement: education || null,
          location: location || null,
          employment_type: employmentType || null,
        }),
      });
      setStatus(`Job posted: ${response.job.title}`);
      setTitle("");
      setDescription("");
      setResponsibilities("");
      setRequiredSkills("");
      setMinExperience("1");
      setEducation("");
      setLocation("");
      setEmploymentType("Full-time");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="HR Suite"
        title="Post a Job"
        subtitle="Create a role to start receiving AI-scored applications instantly."
      />
      <Card variant="glass" className="space-y-4">
        <Input label="Job Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Textarea label="Job Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <Textarea
          label="Responsibilities"
          value={responsibilities}
          onChange={(e) => setResponsibilities(e.target.value)}
        />
        <Input
          label="Required Skills (comma separated)"
          value={requiredSkills}
          onChange={(e) => setRequiredSkills(e.target.value)}
        />
        <Input
          label="Minimum Experience (years)"
          type="number"
          min={0}
          value={minExperience}
          onChange={(e) => setMinExperience(e.target.value)}
        />
        <Input
          label="Education Requirement"
          value={education}
          onChange={(e) => setEducation(e.target.value)}
        />
        <Input label="Location" value={location} onChange={(e) => setLocation(e.target.value)} />
        <Input
          label="Employment Type"
          value={employmentType}
          onChange={(e) => setEmploymentType(e.target.value)}
        />
        {status && <p className="text-sm text-success">{status}</p>}
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button onClick={submit}>Post Job</Button>
      </Card>
    </div>
  );
};
