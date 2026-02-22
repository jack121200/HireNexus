import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Input } from "../../components/Input";
import { apiFetch } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { AuthLayout } from "../../layouts/AuthLayout";

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    role: "candidate";
    full_name: string;
    company_id?: number | null;
  };
};

export const CandidateLogin = () => {
  const { setAuth } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      const data = await apiFetch<AuthResponse>("/api/candidate/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        auth: false,
      });
      setAuth({ token: data.access_token, user: data.user });
      navigate("/candidate/dashboard");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <AuthLayout
      title="Candidate Login"
      subtitle="Access your personalized dashboard, resume insights, and interview sessions."
    >
      <Card className="space-y-4">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button className="w-full" type="submit">
            Sign In
          </Button>
        </form>
        <p className="text-sm text-textMuted">
          No account? <Link className="text-accent" to="/candidate/register">Create one</Link>
        </p>
      </Card>
    </AuthLayout>
  );
};
