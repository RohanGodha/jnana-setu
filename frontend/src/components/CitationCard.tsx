import { useState } from "react";
import { ChevronDown, ChevronRight, BookOpen } from "lucide-react";
import type { Citation } from "../types";
import { AnuyogaBadge } from "./AnuyogaBadge";

export function CitationCard({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-white/5 bg-surface/60 text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-2 px-3 py-2 text-left"
      >
        {open ? (
          <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-text-secondary" />
        ) : (
          <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-text-secondary" />
        )}
        <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display font-semibold text-text-primary">
              {citation.title}
            </span>
            {citation.title_hindi && (
              <span className="text-text-secondary">{citation.title_hindi}</span>
            )}
            <AnuyogaBadge anuyoga={citation.anuyoga} />
          </div>
          <div className="text-xs text-text-secondary">
            {citation.author}
            {citation.chapter ? ` · ${citation.chapter}` : ""}
          </div>
        </div>
      </button>
      {open && citation.excerpt && (
        <p className="border-t border-white/5 px-3 py-2 font-mono text-xs leading-relaxed text-text-secondary">
          {citation.excerpt}
        </p>
      )}
    </div>
  );
}
