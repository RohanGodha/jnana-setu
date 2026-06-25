import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { useChatStore } from "../store/chatStore";
import { useSSE } from "../hooks/useSSE";
import type { Citation } from "../types";
import { Message } from "./Message";

const SUGGESTIONS = [
  "I can't stop feeling angry at someone who hurt me. How do I let go?",
  "I feel like a failure and I'm ashamed of my life. Can you help?",
  "What does Samayasara say about the nature of the soul?",
  "Explain the six substances (dravya) in Jain philosophy.",
];

export function ChatWindow({ initialQuery }: { initialQuery?: string }) {
  const {
    messages,
    addMessage,
    appendToLast,
    setLastCitations,
    markLastError,
    finishStreaming,
    setStreaming,
    isStreaming,
    authorFilter,
    anuyogaFilter,
    language,
  } = useChatStore();

  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const callbacks = useMemo(
    () => ({
      onToken: (token: string) => appendToLast(token),
      onCitations: (citations: Citation[]) => setLastCitations(citations),
      onError: (message: string) => markLastError(message),
      onDone: () => finishStreaming(),
    }),
    [appendToLast, setLastCitations, markLastError, finishStreaming]
  );

  const { startStream } = useSSE(callbacks);

  const send = useCallback(
    async (text: string) => {
      const query = text.trim();
      if (!query || isStreaming) return;
      setInput("");
      addMessage({ id: crypto.randomUUID(), role: "user", content: query });
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        streaming: true,
      });
      setStreaming(true);
      await startStream({
        query,
        author_filter: authorFilter,
        anuyoga_filter: anuyogaFilter,
        language,
      });
    },
    [addMessage, anuyogaFilter, authorFilter, isStreaming, language, setStreaming, startStream]
  );

  // Fire an initial query passed from the Home page once.
  const firedInitial = useRef(false);
  useEffect(() => {
    if (initialQuery && !firedInitial.current) {
      firedInitial.current = true;
      send(initialQuery);
    }
  }, [initialQuery, send]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto px-4 py-6 md:px-8">
        {messages.length === 0 ? (
          <div className="mx-auto max-w-2xl pt-10 text-center">
            <h2 className="font-display text-2xl text-text-primary">
              Ask the library — or share what's on your heart
            </h2>
            <p className="mt-2 text-text-secondary">
              Pose a scholarly question or bring a real struggle. Jnana Setu listens,
              then guides you through the wisdom of 600 Digambar Jain texts — citing
              every source.
            </p>
            <div className="mt-6 grid gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-lg border border-white/5 bg-surface/60 px-4 py-3 text-left text-sm text-text-secondary transition hover:border-accent/40 hover:text-text-primary"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.map((m) => (
              <Message key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-white/5 bg-bg/80 px-4 py-4 backdrop-blur md:px-8">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex max-w-3xl items-end gap-2"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            placeholder="Ask the library…"
            className="max-h-40 flex-1 resize-none rounded-xl border border-white/10 bg-surface px-4 py-3 text-text-primary placeholder:text-text-secondary focus:border-accent/50 focus:outline-none"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-bg transition hover:brightness-110 disabled:opacity-40"
            aria-label="Send"
          >
            {isStreaming ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
