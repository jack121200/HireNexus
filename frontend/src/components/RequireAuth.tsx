import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth, type Role } from "../lib/auth";

export const RequireAuth = ({ role, children }: { role: Role; children: ReactNode }) => {
  const { auth } = useAuth();
  const location = useLocation();

  if (!auth.token || !auth.user) {
    return <Navigate to={role === "candidate" ? "/candidate/login" : "/hr/login"} state={{ from: location }} />;
  }

  if (auth.user.role !== role) {
    return <Navigate to="/forbidden" />;
  }

  return <>{children}</>;
};
