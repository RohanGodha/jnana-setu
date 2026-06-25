import { Sparkles, User as UserIcon } from "lucide-react";
import type { Message as MessageType } from "../types";
import { CitationCard } from "./CitationCard";

export function Message({ message }: { message: MessageType }) {
  const isUser = message.role === "user";
  return (
    <div className="animate-fade-in flex gap-3">
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-white/10" : "bg-accent/20"
        }`}
      >
        {isUser ? (
          <UserIcon className="h-4 w-4 text-text-secondary" />
        ) : (
          <Sparkles className="h-4 w-4 text-accent" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-xs font-medium text-text-secondary">
          {isUser ? "You" : "Jnana Setu"}
        </div>
        <div
          className={`prose-jain whitespace-pre-wrap text-[15px] leading-relaxed ${
            message.error ? "text-red-400" : "text-text-primary"
          }`}
        >
          {message.content}
          {message.streaming && (
            <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-accent align-middle" />
          )}
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
              Sources
            </div>
            {message.citations.map((c, i) => (
              <CitationCard key={`${c.book_id}-${i}`} citation={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
