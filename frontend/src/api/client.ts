import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_URL || "/api";

const TOKEN_KEY = "jnana_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach the JWT to every request.
client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear the token so the app falls back to the login flow.
client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401) {
      setToken(null);
    }
    return Promise.reject(error);
  }
);
