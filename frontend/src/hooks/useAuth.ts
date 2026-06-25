import { useCallback, useEffect, useState } from "react";
import { getToken, setToken } from "../api/client";
import { fetchMe, login as apiLogin, register as apiRegister } from "../api/endpoints";
import { useChatStore } from "../store/chatStore";

export function useAuth() {
  const user = useChatStore((s) => s.user);
  const setUser = useChatStore((s) => s.setUser);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await fetchMe());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [setUser]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await apiLogin(email, password);
      setToken(token);
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await apiRegister(name, email, password);
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, [setUser]);

  return { user, loading, login, register, logout, refresh };
}
