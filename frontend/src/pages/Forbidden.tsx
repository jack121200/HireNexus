import { Link } from "react-router-dom";

import { Button } from "../components/Button";
import { Card } from "../components/Card";

export const Forbidden = () => {
  return (
    <div className="min-h-screen bg-ink text-text">
      <div className="flex min-h-screen items-center justify-center px-6 neo-aurora-bg">
        <Card variant="glass" className="max-w-md space-y-3 text-center">
          <div className="text-xs uppercase tracking-[0.35em] text-textMuted">HireNexus</div>
          <h1 className="font-display text-3xl font-semibold text-white">403 Forbidden</h1>
          <p className="text-sm text-textMuted">You do not have access to this page.</p>
          <Link to="/">
            <Button className="w-full" size="lg">Back to Home</Button>
          </Link>
        </Card>
      </div>
    </div>
  );
};
