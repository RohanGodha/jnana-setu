import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, RefreshCw, TrendingUp, Library } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { fetchRandomSutra, fetchStats, fetchSuggestions, fetchTrending } from "../api/endpoints";

export function Explore() {
  const nav = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [sutra, setSutra] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [trending, setTrending] = useState<{ query: string; count: number }[]>([]);

  const loadSutra = () => fetchRandomSutra().then(setSutra).catch(() => {});

  useEffect(() => {
    fetchStats().then(setStats).catch(() => {});
    fetchSuggestions().then((d) => setSuggestions(d.suggestions)).catch(() => {});
    fetchTrending().then((d) => setTrending(d.trending)).catch(() => {});
    loadSutra();
  }, []);

  const ask = (q: string) => nav(`/chat?q=${encodeURIComponent(q)}`);

  const stat = (label: string, value: string | number) => (
    <div className="rounded-2xl border border-white/10 bg-surface p-5 text-center">
      <p className="font-display text-3xl text-accent">{value}</p>
      <p className="text-xs uppercase tracking-wide text-text-secondary">{label}</p>
    </div>
  );

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="flex items-center gap-3">
          <Library className="h-6 w-6 text-accent" />
          <h1 className="font-display text-3xl text-text-primary">Explore the corpus</h1>
        </div>

        {stats && (
          <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {stat("Books", stats.total_books)}
            {stat("Passages", (stats.total_chunks ?? 0).toLocaleString())}
            {stat("Sources", Object.keys(stats.sources ?? {}).length)}
            {stat("Categories", Object.keys(stats.anuyogas ?? {}).length)}
          </div>
        )}

        {stats?.sources && (
          <p className="mt-4 text-center text-sm text-text-secondary">
            From{" "}
            {Object.entries(stats.sources)
              .map(([k, v]) => `${v} ${k}`)
              .join(" · ")}
          </p>
        )}

        {/* Random sutra */}
        <div className="mt-10 rounded-2xl border border-accent/20 bg-surface p-6">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex items-center gap-2 text-sm uppercase tracking-wide text-accent">
              <Sparkles className="h-4 w-4" /> Random passage
            </span>
            <button onClick={loadSutra} className="text-text-secondary hover:text-accent">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          {sutra && (
            <>
              <p className="font-mono text-sm leading-relaxed text-text-primary">
                {sutra.excerpt}
              </p>
              <p className="mt-3 text-xs text-text-secondary">— {sutra.title}</p>
            </>
          )}
        </div>

        {/* Suggested questions */}
        <h2 className="mt-10 mb-3 font-display text-xl text-text-primary">Start with a question</h2>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              className="rounded-full border border-white/10 bg-surface px-4 py-2 text-sm text-text-secondary hover:border-accent/40 hover:text-text-primary"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Trending */}
        {trending.length > 0 && (
          <>
            <h2 className="mt-10 mb-3 flex items-center gap-2 font-display text-xl text-text-primary">
              <TrendingUp className="h-5 w-5 text-accent" /> Trending
            </h2>
            <div className="space-y-2">
              {trending.map((t, i) => (
                <button
                  key={i}
                  onClick={() => ask(t.query)}
                  className="block w-full rounded-xl border border-white/10 bg-surface px-4 py-2 text-left text-sm text-text-secondary hover:text-text-primary"
                >
                  {t.query} <span className="text-xs text-accent">×{t.count}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
