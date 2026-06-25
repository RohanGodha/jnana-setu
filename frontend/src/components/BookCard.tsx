import type { BookSummary } from "../types";
import { AnuyogaBadge } from "./AnuyogaBadge";

export function BookCard({ book }: { book: BookSummary }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-white/5 bg-surface/60 p-4 transition hover:border-accent/30">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-display text-lg leading-tight text-text-primary">
          {book.title}
        </h3>
      </div>
      {book.title_hindi && (
        <div className="text-sm text-text-secondary">{book.title_hindi}</div>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
        <AnuyogaBadge anuyoga={book.anuyoga} />
        <span className="rounded-full bg-white/5 px-2 py-0.5 text-xs capitalize text-text-secondary">
          {book.language}
        </span>
        {book.century && (
          <span className="text-xs text-text-secondary">{book.century}</span>
        )}
      </div>
      <div className="text-xs text-text-secondary">{book.author}</div>
      {book.total_chunks > 0 && (
        <div className="text-[11px] text-accent/70">
          {book.total_chunks.toLocaleString()} indexed passages
        </div>
      )}
    </div>
  );
}
