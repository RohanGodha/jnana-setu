import { client } from "./client";
import type {
  AuthorSummary,
  BookDetail,
  BookList,
  DailyReflectionData,
  User,
} from "../types";

// --- Auth -------------------------------------------------------------------
export async function register(name: string, email: string, password: string) {
  const { data } = await client.post("/auth/register", { name, email, password });
  return data;
}

export async function login(email: string, password: string): Promise<string> {
  const { data } = await client.post("/auth/login", { email, password });
  return data.access_token as string;
}

export async function fetchMe(): Promise<User> {
  const { data } = await client.get("/auth/me");
  return data;
}

// --- Books ------------------------------------------------------------------
export interface BookQuery {
  page?: number;
  per_page?: number;
  anuyoga?: string;
  author_slug?: string;
  language?: string;
  search?: string;
}

export async function fetchBooks(params: BookQuery = {}): Promise<BookList> {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "" && v !== "all")
  );
  const { data } = await client.get("/books", { params: cleaned });
  return data;
}

export async function fetchBook(id: string): Promise<BookDetail> {
  const { data } = await client.get(`/books/${id}`);
  return data;
}

// --- Authors ----------------------------------------------------------------
export async function fetchAuthors(): Promise<AuthorSummary[]> {
  const { data } = await client.get("/authors");
  return data;
}

// --- Daily reflection -------------------------------------------------------
export async function fetchDailyReflection(): Promise<DailyReflectionData> {
  const { data } = await client.post("/daily-reflection");
  return data;
}
