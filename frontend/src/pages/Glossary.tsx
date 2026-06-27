import { useEffect, useMemo, useState } from "react";
import { Search, BookA } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { fetchGlossary, type GlossaryTerm } from "../api/endpoints";

export function Glossary() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    fetchGlossary().then((d) => setTerms(d.terms)).catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    const s = q.toLowerCase().trim();
    if (!s) return terms;
    return terms.filter(
      (t) =>
        t.term.toLowerCase().includes(s) ||
        t.meaning.toLowerCase().includes(s) ||
        t.hindi.includes(q)
    );
  }, [q, terms]);

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <div className="flex items-center gap-3">
          <BookA className="h-6 w-6 text-accent" />
          <h1 className="font-display text-3xl text-text-primary">Glossary of Jain terms</h1>
        </div>

        <div className="mt-6 flex items-center gap-2 rounded-xl border border-white/10 bg-surface px-3">
          <Search className="h-4 w-4 text-text-secondary" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search a term…"
            className="w-full bg-transparent py-2.5 text-text-primary focus:outline-none"
          />
        </div>

        <div className="mt-6 space-y-3">
          {filtered.map((t) => (
            <div key={t.term} className="rounded-2xl border border-white/10 bg-surface p-5">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-display text-lg text-text-primary">{t.term}</span>
                <span className="text-accent">{t.hindi}</span>
              </div>
              <p className="mt-1 text-sm leading-relaxed text-text-secondary">{t.meaning}</p>
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-text-secondary">No term matches “{q}”.</p>
          )}
        </div>
      </main>
    </div>
  );
}
