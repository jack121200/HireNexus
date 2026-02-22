import { Link } from "react-router-dom";

import { Button } from "../components/Button";
import { Card } from "../components/Card";

export const NotFound = () => {
  return (
    <div className="min-h-screen bg-ink text-text">
      <div className="flex min-h-screen items-center justify-center px-6 neo-aurora-bg">
        <Card variant="glass" className="max-w-md space-y-3 text-center">
          <div className="text-xs uppercase tracking-[0.35em] text-textMuted">HireNexus</div>
          <h1 className="font-display text-3xl font-semibold text-white">404 Not Found</h1>
          <p className="text-sm text-textMuted">The page you are looking for does not exist.</p>
          <Link to="/">
            <Button className="w-full" size="lg">Back to Home</Button>
          </Link>
        </Card>
      </div>
    </div>
  );
};
