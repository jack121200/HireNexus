import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type Role = "candidate" | "hr";

export type AuthUser = {
  id: number;
  email: string;
  role: Role;
  full_name: string;
  company_id?: number | null;
};

export type AuthState = {
  token: string | null;
  user: AuthUser | null;
};

const TOKEN_KEY = "hn_token";
const USER_KEY = "hn_user";

const AuthContext = createContext<{
  auth: AuthState;
  setAuth: (state: AuthState) => void;
  logout: () => void;
}>({
  auth: { token: null, user: null },
  setAuth: () => {},
  logout: () => {},
});

const readAuth = (): AuthState => {
  const token = localStorage.getItem(TOKEN_KEY);
  const userRaw = localStorage.getItem(USER_KEY);
  if (!token || !userRaw) {
    return { token: null, user: null };
  }
  try {
    const user = JSON.parse(userRaw) as AuthUser;
    return { token, user };
  } catch {
    return { token: null, user: null };
  }
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [auth, setAuthState] = useState<AuthState>(() => readAuth());

  const setAuth = (state: AuthState) => {
    if (state.token && state.user) {
      localStorage.setItem(TOKEN_KEY, state.token);
      localStorage.setItem(USER_KEY, JSON.stringify(state.user));
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    setAuthState(state);
  };

  const logout = () => setAuth({ token: null, user: null });

  const value = useMemo(() => ({ auth, setAuth, logout }), [auth]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);

export const getAuthToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};
