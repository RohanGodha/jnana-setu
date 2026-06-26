export type Tier = "free" | "premium" | "scholar" | "institutional";

export interface User {
  id: string;
  name: string;
  email: string;
  tier: Tier;
  queries_today: number;
  daily_limit: number;
  is_admin?: boolean;
  is_pro?: boolean;
  pro_until?: string | null;
}

export interface PlanInfo {
  plan: string;
  price_inr: number;
  days: number;
  upi_configured: boolean;
  benefits: string[];
}

export interface UpiOrder {
  payment_id: string;
  amount: number;
  currency: string;
  vpa: string;
  payee_name: string;
  upi_link: string;
  qr_svg: string;
  configured: boolean;
  instructions: string;
  already_pro?: boolean;
  message?: string;
}

export interface Bookmark {
  id: string;
  book_id: string;
  title: string;
  author: string;
  excerpt: string;
  note: string;
  created_at: string;
}

export interface Payment {
  id: string;
  user_id: string;
  amount: number;
  plan: string;
  status: string;
  txn_ref: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStats {
  users: number;
  pro_users: number;
  paid_payments: number;
  revenue_inr: number;
  total_queries: number;
}

export interface Citation {
  book_id: string;
  title: string;
  title_hindi: string;
  author: string;
  anuyoga: string;
  chapter: string;
  excerpt: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
  error?: boolean;
}

export interface QueryRequest {
  query: string;
  author_filter: string[];
  anuyoga_filter: string | null;
  language: "en" | "hi";
}

export interface BookSummary {
  id: string;
  title: string;
  title_hindi: string;
  author: string;
  author_slug: string;
  anuyoga: string;
  language: string;
  century: string;
  total_chunks: number;
}

export interface BookList {
  total: number;
  page: number;
  per_page: number;
  books: BookSummary[];
}

export interface BookDetail extends BookSummary {
  anuyoga_label: string;
  description: string;
  source_url: string;
}

export interface AuthorSummary {
  slug: string;
  name: string;
  book_count: number;
  primary_anuyoga: string;
  era: string;
}

export interface DailyReflectionData {
  text: string;
  text_translated: string;
  reflection: string;
  source: { title: string; author: string; chapter: string };
  generated_at: string;
}
