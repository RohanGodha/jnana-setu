import { useQuery } from "@tanstack/react-query";
import { Loader2, Quote } from "lucide-react";
import { fetchDailyReflection } from "../api/endpoints";

export function DailyReflection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["daily-reflection"],
    queryFn: fetchDailyReflection,
    staleTime: 1000 * 60 * 60,
  });

  return (
    <div className="relative overflow-hidden rounded-2xl border border-accent/20 bg-surface/70 p-6">
      <div className="mb-3 flex items-center gap-2 text-accent">
        <Quote className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-widest">
          Daily Reflection
        </span>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-text-secondary">
          <Loader2 className="h-4 w-4 animate-spin" /> Drawing today's sutra…
        </div>
      ) : isError || !data ? (
        <p className="text-text-secondary">Could not load today's reflection.</p>
      ) : (
        <div>
          <p className="font-display text-lg leading-relaxed text-text-primary">
            “{data.text}”
          </p>
          {data.text_translated && (
            <p className="mt-2 text-sm text-text-secondary">{data.text_translated}</p>
          )}
          {data.reflection && (
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              {data.reflection}
            </p>
          )}
          <div className="mt-4 text-xs text-accent/80">
            — {data.source.title}, {data.source.author}
            {data.source.chapter ? `, ${data.source.chapter}` : ""}
          </div>
        </div>
      )}
    </div>
  );
}
