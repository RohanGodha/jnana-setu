import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { useAuth } from "../hooks/useAuth";

export function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") await register(name, email, password);
      else await login(email, password);
      navigate("/chat");
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
          (mode === "register" ? "Registration failed." : "Invalid email or password.")
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto flex max-w-md flex-col px-4 py-20">
        <h1 className="text-center font-display text-3xl text-text-primary">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="mt-2 text-center text-sm text-text-secondary">
          {mode === "login"
            ? "Sign in to continue your study."
            : "Begin with 3 free queries a day."}
        </p>

        <form onSubmit={submit} className="mt-8 space-y-4">
          {mode === "register" && (
            <Field
              label="Name"
              value={name}
              onChange={setName}
              type="text"
              autoComplete="name"
            />
          )}
          <Field
            label="Email"
            value={email}
            onChange={setEmail}
            type="email"
            autoComplete="email"
          />
          <Field
            label="Password"
            value={password}
            onChange={setPassword}
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-2.5 font-medium text-bg hover:brightness-110 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError("");
          }}
          className="mt-6 text-center text-sm text-accent hover:underline"
        >
          {mode === "login"
            ? "Don't have an account? Sign up"
            : "Already have an account? Sign in"}
        </button>
      </main>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type: string;
  autoComplete?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-text-secondary">{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        required
        className="w-full rounded-xl border border-white/10 bg-surface px-4 py-2.5 text-text-primary focus:border-accent/50 focus:outline-none"
      />
    </label>
  );
}
