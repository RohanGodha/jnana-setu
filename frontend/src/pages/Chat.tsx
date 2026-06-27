import { Link, useLocation, useSearchParams } from "react-router-dom";
import { NavBar } from "../components/NavBar";
import { AuthorFilter } from "../components/AuthorFilter";
import { ChatWindow } from "../components/ChatWindow";
import { useAuth } from "../hooks/useAuth";

export function Chat() {
  const location = useLocation();
  const [params] = useSearchParams();
  const initialQuery =
    (location.state as { initialQuery?: string } | null)?.initialQuery ||
    params.get("q") ||
    undefined;
  const { user } = useAuth();

  return (
    <div className="flex h-screen flex-col">
      <NavBar />
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-72 shrink-0 overflow-y-auto border-r border-white/5 bg-surface/40 p-4 md:block">
          <AuthorFilter />
          {user && !user.is_admin && !user.is_pro && (
            <div className="mt-6 rounded-lg border border-accent/20 bg-accent/5 p-3 text-xs text-text-secondary">
              Free tier: {user.queries_today}/{user.daily_limit} queries used today.
              <Link
                to="/pro"
                className="mt-2 block rounded-md bg-accent px-3 py-1.5 text-center font-medium text-bg hover:brightness-110"
              >
                Upgrade to Pro ✦
              </Link>
            </div>
          )}
        </aside>
        <main className="min-w-0 flex-1">
          <ChatWindow initialQuery={initialQuery} />
        </main>
      </div>
    </div>
  );
}
