import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Loader2, Search } from "lucide-react";
import { fetchBooks } from "../api/endpoints";
import { BookCard } from "./BookCard";

const ANUYOGA_TABS = [
  { slug: "all", label: "All" },
  { slug: "dravyanuyog", label: "Philosophy" },
  { slug: "charananuyog", label: "Ethics" },
  { slug: "prathamanuyoga", label: "History" },
  { slug: "karnanuyoga", label: "Cosmology" },
];

const PER_PAGE = 24;

export function BookGrid() {
  const [search, setSearch] = useState("");
  const [anuyoga, setAnuyoga] = useState("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["books", { search, anuyoga, page }],
    queryFn: () =>
      fetchBooks({
        search: search || undefined,
        anuyoga: anuyoga === "all" ? undefined : anuyoga,
        page,
        per_page: PER_PAGE,
      }),
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  return (
    <div>
      <div className="sticky top-0 z-10 space-y-3 bg-bg/90 pb-4 pt-2 backdrop-blur">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search books…"
            className="w-full rounded-xl border border-white/10 bg-surface py-2.5 pl-10 pr-4 text-text-primary placeholder:text-text-secondary focus:border-accent/50 focus:outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {ANUYOGA_TABS.map((t) => (
            <button
              key={t.slug}
              onClick={() => {
                setAnuyoga(t.slug);
                setPage(1);
              }}
              className={`rounded-full px-3 py-1 text-sm transition ${
                anuyoga === t.slug
                  ? "bg-accent text-bg"
                  : "bg-surface text-text-secondary hover:text-text-primary"
              }`}
            >
              {t.label}
            </button>
          ))}
          <span className="ml-auto self-center text-sm text-text-secondary">
            {total.toLocaleString()} books
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 py-20 text-text-secondary">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading library…
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data?.books.map((b) => (
              <BookCard key={b.id} book={b} />
            ))}
          </div>
          {data && data.books.length === 0 && (
            <p className="py-16 text-center text-text-secondary">
              No books match your search.
            </p>
          )}

          <div className="mt-8 flex items-center justify-center gap-4">
            <button
              disabled={page <= 1 || isFetching}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-text-secondary disabled:opacity-30"
            >
              Previous
            </button>
            <span className="text-sm text-text-secondary">
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages || isFetching}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-text-secondary disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
