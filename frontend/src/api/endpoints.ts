import { client } from "./client";
import type {
  AdminStats,
  AuthorSummary,
  BookDetail,
  BookList,
  Bookmark,
  DailyReflectionData,
  Payment,
  PlanInfo,
  UpiOrder,
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

// --- Billing (UPI) ----------------------------------------------------------
export async function fetchPlan(): Promise<PlanInfo> {
  const { data } = await client.get("/billing/plan");
  return data;
}

export async function createOrder(): Promise<UpiOrder> {
  const { data } = await client.post("/billing/create-order", { plan: "pro" });
  return data;
}

export async function submitPayment(payment_id: string, txn_ref: string) {
  const { data } = await client.post("/billing/submit", { payment_id, txn_ref });
  return data;
}

export async function myPayments(): Promise<{ payments: Payment[] }> {
  const { data } = await client.get("/billing/my-payments");
  return data;
}

// --- Bookmarks --------------------------------------------------------------
export async function listBookmarks(): Promise<{ bookmarks: Bookmark[] }> {
  const { data } = await client.get("/bookmarks");
  return data;
}

export async function addBookmark(b: {
  book_id?: string;
  title: string;
  author: string;
  excerpt: string;
  note?: string;
}) {
  const { data } = await client.post("/bookmarks", b);
  return data;
}

export async function deleteBookmark(id: string) {
  const { data } = await client.delete(`/bookmarks/${id}`);
  return data;
}

// --- Stats / discovery ------------------------------------------------------
export async function fetchStats() {
  const { data } = await client.get("/stats");
  return data;
}

export async function fetchSuggestions(): Promise<{ suggestions: string[] }> {
  const { data } = await client.get("/suggestions");
  return data;
}

export async function fetchTrending(): Promise<{ trending: { query: string; count: number }[] }> {
  const { data } = await client.get("/trending");
  return data;
}

export async function fetchRandomSutra(): Promise<{
  book_id: string;
  title: string;
  author: string;
  anuyoga: string;
  excerpt: string;
}> {
  const { data } = await client.get("/random-sutra");
  return data;
}

export interface GlossaryTerm {
  term: string;
  hindi: string;
  meaning: string;
}

export async function fetchGlossary(q = ""): Promise<{ terms: GlossaryTerm[] }> {
  const { data } = await client.get("/glossary", { params: q ? { q } : {} });
  return data;
}

// --- Admin ------------------------------------------------------------------
export async function adminStats(): Promise<AdminStats> {
  const { data } = await client.get("/admin/stats");
  return data;
}

export async function adminPayments(status?: string): Promise<{ payments: Payment[] }> {
  const { data } = await client.get("/admin/payments", { params: status ? { status } : {} });
  return data;
}

export async function adminApprove(id: string) {
  const { data } = await client.post(`/admin/payments/${id}/approve`);
  return data;
}

export async function adminReject(id: string) {
  const { data } = await client.post(`/admin/payments/${id}/reject`);
  return data;
}
