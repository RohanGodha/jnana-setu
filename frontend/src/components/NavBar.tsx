import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function NavBar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();

  const link = (to: string, label: string) => (
    <Link
      to={to}
      className={`text-sm transition ${
        pathname === to ? "text-accent" : "text-text-secondary hover:text-text-primary"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="border-b border-white/5 bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link to="/" className="flex items-baseline gap-2">
          <span className="font-display text-xl text-text-primary">ज्ञान सेतु</span>
          <span className="text-xs uppercase tracking-widest text-accent">Jnana Setu</span>
        </Link>

        <nav className="flex items-center gap-5">
          {link("/chat", "Chat")}
          {link("/explore", "Explore")}
          {link("/search", "Search")}
          {link("/books", "Library")}
          {link("/glossary", "Glossary")}
          {user && link("/bookmarks", "Saved")}
          {user && !user.is_admin && !user.is_pro && link("/pro", "Upgrade")}
          {user?.is_admin && link("/admin", "Admin")}
          {user ? (
            <div className="flex items-center gap-3">
              <span className="hidden text-xs text-text-secondary sm:inline">
                {user.is_admin
                  ? "admin"
                  : user.is_pro
                  ? "Pro"
                  : `${user.queries_today}/${user.daily_limit} today`}
              </span>
              <button
                onClick={logout}
                className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary"
              >
                Sign out
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-bg hover:brightness-110"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
