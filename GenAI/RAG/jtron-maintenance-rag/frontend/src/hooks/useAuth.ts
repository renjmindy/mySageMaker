import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { User } from "../types";

type AuthState =
  | { status: "loading" }
  | { status: "guest" }
  | { status: "authed"; user: User };

export function useAuth() {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const refresh = useCallback(async () => {
    try {
      const user = await api.me();
      setState({ status: "authed", user });
    } catch {
      setState({ status: "guest" });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const user = await api.login(email, password);
      setState({ status: "authed", user });
    },
    [],
  );

  const register = useCallback(
    async (email: string, password: string, display_name: string) => {
      const user = await api.register(email, password, display_name);
      setState({ status: "authed", user });
    },
    [],
  );

  const logout = useCallback(async () => {
    await api.logout();
    setState({ status: "guest" });
  }, []);

  return { state, login, register, logout, refresh };
}
