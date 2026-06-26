import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark as BookmarkIcon, Trash2, Loader2 } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { useAuth } from "../hooks/useAuth";
import { deleteBookmark, listBookmarks } from "../api/endpoints";
import type { Bookmark } from "../types";

export function Bookmarks() {
  const { user } = useAuth();
  const [items, setItems] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () =>
    listBookmarks()
      .then((d) => setItems(d.bookmarks))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));

  useEffect(() => {
    if (user) load();
    else setLoading(false);
  }, [user]);

  const remove = async (id: string) => {
    await deleteBookmark(id);
    setItems((x) => x.filter((b) => b.id !== id));
  };

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <div className="flex items-center gap-3">
          <BookmarkIcon className="h-6 w-6 text-accent" />
          <h1 className="font-display text-3xl text-text-primary">Saved passages</h1>
        </div>

        {!user && (
          <p className="mt-6 text-text-secondary">
            Please <Link to="/login" className="text-accent hover:underline">sign in</Link> to view bookmarks.
          </p>
        )}

        {user && loading && (
          <div className="mt-10 flex justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
          </div>
        )}

        {user && !loading && items.length === 0 && (
          <p className="mt-8 text-text-secondary">
            No bookmarks yet. Save passages from chat answers using the bookmark icon.
          </p>
        )}

        <div className="mt-8 space-y-4">
          {items.map((b) => (
            <div key={b.id} className="rounded-2xl border border-white/10 bg-surface p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-text-primary">{b.title}</p>
                  <p className="text-xs text-text-secondary">{b.author}</p>
                </div>
                <button
                  onClick={() => remove(b.id)}
                  className="text-text-secondary hover:text-red-400"
                  title="Remove"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">{b.excerpt}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
