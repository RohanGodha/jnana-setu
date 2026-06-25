import { create } from "zustand";
import type { Citation, Message, User } from "../types";

interface ChatStore {
  messages: Message[];
  authorFilter: string[];
  anuyogaFilter: string;
  language: "en" | "hi";
  isStreaming: boolean;
  user: User | null;

  addMessage: (msg: Message) => void;
  appendToLast: (token: string) => void;
  setLastCitations: (citations: Citation[]) => void;
  markLastError: (content: string) => void;
  finishStreaming: () => void;

  setAuthorFilter: (authors: string[]) => void;
  setAnuyogaFilter: (anuyoga: string) => void;
  setLanguage: (lang: "en" | "hi") => void;
  setStreaming: (v: boolean) => void;
  setUser: (user: User | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  authorFilter: ["all"],
  anuyogaFilter: "all_texts",
  language: "en",
  isStreaming: false,
  user: null,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendToLast: (token) =>
    set((s) => {
      const messages = [...s.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: last.content + token };
      }
      return { messages };
    }),

  setLastCitations: (citations) =>
    set((s) => {
      const messages = [...s.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = { ...last, citations };
      }
      return { messages };
    }),

  markLastError: (content) =>
    set((s) => {
      const messages = [...s.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          content,
          error: true,
          streaming: false,
        };
      }
      return { messages, isStreaming: false };
    }),

  finishStreaming: () =>
    set((s) => {
      const messages = [...s.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = { ...last, streaming: false };
      }
      return { messages, isStreaming: false };
    }),

  setAuthorFilter: (authors) => set({ authorFilter: authors }),
  setAnuyogaFilter: (anuyoga) => set({ anuyogaFilter: anuyoga }),
  setLanguage: (language) => set({ language }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setUser: (user) => set({ user }),
  clearMessages: () => set({ messages: [] }),
}));
