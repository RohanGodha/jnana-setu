import { useLocation } from "react-router-dom";
import { NavBar } from "../components/NavBar";
import { AuthorFilter } from "../components/AuthorFilter";
import { ChatWindow } from "../components/ChatWindow";
import { useAuth } from "../hooks/useAuth";

export function Chat() {
  const location = useLocation();
  const initialQuery = (location.state as { initialQuery?: string } | null)?.initialQuery;
  const { user } = useAuth();

  return (
    <div className="flex h-screen flex-col">
      <NavBar />
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-72 shrink-0 overflow-y-auto border-r border-white/5 bg-surface/40 p-4 md:block">
          <AuthorFilter />
          {user?.tier === "free" && (
            <p className="mt-6 rounded-lg border border-accent/20 bg-accent/5 p-3 text-xs text-text-secondary">
              Free tier: {user.queries_today}/{user.daily_limit} queries used today.
              Upgrade for unlimited queries, Hindi answers and full citation excerpts.
            </p>
          )}
        </aside>
        <main className="min-w-0 flex-1">
          <ChatWindow initialQuery={initialQuery} />
        </main>
      </div>
    </div>
  );
}
