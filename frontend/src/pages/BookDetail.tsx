import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, MessageSquare, Loader2 } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { AnuyogaBadge } from "../components/AnuyogaBadge";
import { fetchBook, fetchBookPassages, fetchRelatedBooks } from "../api/endpoints";
import type { BookDetail as Detail, BookSummary } from "../types";

export function BookDetail() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [book, setBook] = useState<Detail | null>(null);
  const [passages, setPassages] = useState<{ chapter: string; excerpt: string }[]>([]);
  const [related, setRelated] = useState<BookSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchBook(id).then(setBook).catch(() => setBook(null)).finally(() => setLoading(false));
    fetchBookPassages(id).then((d) => setPassages(d.passages)).catch(() => {});
    fetchRelatedBooks(id).then((d) => setRelated(d.related)).catch(() => {});
  }, [id]);

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <Link to="/books" className="mb-6 inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
          <ArrowLeft className="h-4 w-4" /> Library
        </Link>

        {loading && (
          <div className="flex justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
          </div>
        )}

        {!loading && !book && <p className="text-text-secondary">Book not found.</p>}

        {book && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-3xl text-text-primary">{book.title}</h1>
              <AnuyogaBadge anuyoga={book.anuyoga} />
            </div>
            {book.title_hindi && <p className="mt-1 text-accent">{book.title_hindi}</p>}
            <p className="mt-2 text-text-secondary">
              {book.author}
              {book.century ? ` · ${book.century}` : ""} · {book.language}
            </p>
            {book.description && (
              <p className="mt-4 text-sm leading-relaxed text-text-secondary">{book.description}</p>
            )}

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() =>
                  nav(`/chat?q=${encodeURIComponent(`What does ${book.title} teach?`)}`)
                }
                className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-bg hover:brightness-110"
              >
                <MessageSquare className="h-4 w-4" /> Ask about this book
              </button>
              {book.source_url && (
                <a
                  href={book.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
                >
                  <ExternalLink className="h-4 w-4" /> Source
                </a>
              )}
            </div>

            {passages.length > 0 && (
              <>
                <h2 className="mt-10 mb-3 font-display text-xl text-text-primary">Passages</h2>
                <div className="space-y-3">
                  {passages.map((p, i) => (
                    <div key={i} className="rounded-2xl border border-white/10 bg-surface p-4">
                      {p.chapter && p.chapter !== "Unknown" && (
                        <p className="mb-1 text-xs uppercase tracking-wide text-accent">{p.chapter}</p>
                      )}
                      <p className="font-mono text-xs leading-relaxed text-text-secondary">{p.excerpt}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            {related.length > 0 && (
              <>
                <h2 className="mt-10 mb-3 font-display text-xl text-text-primary">Related</h2>
                <div className="grid gap-3 sm:grid-cols-2">
                  {related.map((r) => (
                    <Link
                      key={r.id}
                      to={`/books/${r.id}`}
                      className="rounded-xl border border-white/10 bg-surface p-4 hover:border-accent/40"
                    >
                      <p className="font-medium text-text-primary">{r.title}</p>
                      <p className="text-xs text-text-secondary">{r.author}</p>
                    </Link>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
