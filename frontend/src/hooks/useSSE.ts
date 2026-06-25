import { useCallback } from "react";
import { API_BASE, getToken } from "../api/client";
import type { Citation, QueryRequest } from "../types";

interface SSECallbacks {
  onToken: (token: string) => void;
  onCitations: (citations: Citation[]) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

/**
 * Streams POST /query via fetch + ReadableStream and parses the SSE protocol
 * emitted by FastAPI:
 *
 *   event: token
 *   data: "..."
 *
 *   event: citations
 *   data: [ ... ]
 *
 *   event: done
 *   data: {}
 */
export function useSSE(callbacks: SSECallbacks) {
  const startStream = useCallback(
    async (payload: QueryRequest) => {
      const token = getToken();
      let response: Response;
      try {
        response = await fetch(`${API_BASE}/query`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(payload),
        });
      } catch {
        callbacks.onError("Could not reach the server.");
        callbacks.onDone();
        return;
      }

      if (!response.ok) {
        let detail = `Request failed (${response.status}).`;
        if (response.status === 429)
          detail = "Daily limit reached. Upgrade for unlimited access.";
        if (response.status === 403)
          detail = "Hindi responses require Premium.";
        if (response.status === 401) detail = "Please sign in to ask a question.";
        try {
          const body = await response.json();
          if (body?.detail) detail = body.detail;
        } catch {
          /* ignore */
        }
        callbacks.onError(detail);
        callbacks.onDone();
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError("Streaming not supported by this browser.");
        callbacks.onDone();
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      const handleEvent = (raw: string) => {
        const lines = raw.split("\n");
        let event = "message";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
        }
        if (!dataStr) return;
        let data: unknown;
        try {
          data = JSON.parse(dataStr);
        } catch {
          data = dataStr;
        }
        switch (event) {
          case "token":
            callbacks.onToken(String(data));
            break;
          case "citations":
            callbacks.onCitations(data as Citation[]);
            break;
          case "error":
            callbacks.onError(
              (data as { message?: string })?.message ?? "An error occurred."
            );
            break;
          case "done":
            callbacks.onDone();
            break;
        }
      };

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let sep: number;
        // SSE events are separated by a blank line.
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          handleEvent(rawEvent);
        }
      }
      if (buffer.trim()) handleEvent(buffer);
      callbacks.onDone();
    },
    [callbacks]
  );

  return { startStream };
}
