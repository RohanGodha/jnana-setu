import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search as SearchIcon, Loader2, MessageSquare } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { AnuyogaBadge } from "../components/AnuyogaBadge";
import { searchPassages } from "../api/endpoints";

type Hit = { book_id: string; title: string; author: string; anuyoga: string; chapter: string; excerpt: string };

export function Search() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const run = async (e: FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return;
    setLoading(true);
    setDone(false);
    try {
      const d = await searchPassages(q.trim());
      setHits(d.results);
    } catch {
      setHits([]);
    } finally {
      setLoading(false);
      setDone(true);
    }
  };

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="font-display text-3xl text-text-primary">Passage search</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Find exact passages across 1,300+ texts — no AI, just the sources.
        </p>

        <form onSubmit={run} className="mt-6 flex items-center gap-2 rounded-xl border border-white/10 bg-surface px-3">
          <SearchIcon className="h-4 w-4 text-text-secondary" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. nature of the soul, karma bondage…"
            className="w-full bg-transparent py-3 text-text-primary focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !q.trim()}
            className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-bg hover:brightness-110 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </button>
        </form>

        <div className="mt-6 space-y-3">
          {hits.map((h, i) => (
            <div key={i} className="rounded-2xl border border-white/10 bg-surface p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-display text-text-primary">{h.title}</span>
                <AnuyogaBadge anuyoga={h.anuyoga} />
              </div>
              <p className="text-xs text-text-secondary">{h.author}</p>
              <p className="mt-2 font-mono text-xs leading-relaxed text-text-secondary">{h.excerpt}</p>
            </div>
          ))}
          {done && !loading && hits.length === 0 && (
            <p className="text-text-secondary">No passages found. Try different words.</p>
          )}
        </div>

        {done && (
          <button
            onClick={() => nav(`/chat?q=${encodeURIComponent(q)}`)}
            className="mt-6 inline-flex items-center gap-2 text-sm text-accent hover:underline"
          >
            <MessageSquare className="h-4 w-4" /> Ask this as a question instead
          </button>
        )}
      </main>
    </div>
  );
}
