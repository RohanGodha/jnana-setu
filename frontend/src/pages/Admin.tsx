import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Check, X, ShieldCheck } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { useAuth } from "../hooks/useAuth";
import { adminApprove, adminPayments, adminReject, adminStats } from "../api/endpoints";
import type { AdminStats, Payment } from "../types";

export function Admin() {
  const { user, loading: authLoading } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    Promise.all([adminStats(), adminPayments()])
      .then(([s, p]) => {
        setStats(s);
        setPayments(p.payments);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (user?.is_admin) load();
    else if (!authLoading) setLoading(false);
  }, [user, authLoading]);

  const act = async (id: string, kind: "approve" | "reject") => {
    setBusy(id);
    try {
      if (kind === "approve") await adminApprove(id);
      else await adminReject(id);
      load();
    } finally {
      setBusy(null);
    }
  };

  if (!authLoading && !user?.is_admin) {
    return (
      <div className="min-h-screen">
        <KnowledgeLine />
        <NavBar />
        <main className="mx-auto max-w-2xl px-4 py-20 text-center">
          <p className="text-text-secondary">
            Admins only. <Link to="/" className="text-accent hover:underline">Go home</Link>
          </p>
        </main>
      </div>
    );
  }

  const stat = (label: string, value: string | number) => (
    <div className="rounded-2xl border border-white/10 bg-surface p-5">
      <p className="text-2xl font-display text-accent">{value}</p>
      <p className="text-xs uppercase tracking-wide text-text-secondary">{label}</p>
    </div>
  );

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-accent" />
          <h1 className="font-display text-3xl text-text-primary">Admin</h1>
        </div>

        {loading && (
          <div className="mt-10 flex justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
          </div>
        )}

        {!loading && stats && (
          <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-5">
            {stat("Users", stats.users)}
            {stat("Pro", stats.pro_users)}
            {stat("Paid", stats.paid_payments)}
            {stat("Revenue ₹", stats.revenue_inr)}
            {stat("Queries", stats.total_queries)}
          </div>
        )}

        {!loading && (
          <>
            <h2 className="mt-10 mb-3 font-display text-xl text-text-primary">Payments</h2>
            {payments.length === 0 && (
              <p className="text-text-secondary">No payments yet.</p>
            )}
            <div className="space-y-3">
              {payments.map((p) => (
                <div
                  key={p.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-surface p-4"
                >
                  <div className="text-sm">
                    <p className="text-text-primary">
                      ₹{p.amount} · <span className="text-text-secondary">{p.plan}</span> ·{" "}
                      <span
                        className={
                          p.status === "paid"
                            ? "text-green-400"
                            : p.status === "rejected"
                            ? "text-red-400"
                            : "text-yellow-300"
                        }
                      >
                        {p.status}
                      </span>
                    </p>
                    <p className="text-xs text-text-secondary">
                      txn: {p.txn_ref || "—"} · {p.user_id}
                    </p>
                  </div>
                  {p.status === "pending" && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => act(p.id, "approve")}
                        disabled={busy === p.id}
                        className="flex items-center gap-1 rounded-lg bg-green-500/20 px-3 py-1.5 text-sm text-green-300 hover:bg-green-500/30"
                      >
                        <Check className="h-4 w-4" /> Approve
                      </button>
                      <button
                        onClick={() => act(p.id, "reject")}
                        disabled={busy === p.id}
                        className="flex items-center gap-1 rounded-lg bg-red-500/20 px-3 py-1.5 text-sm text-red-300 hover:bg-red-500/30"
                      >
                        <X className="h-4 w-4" /> Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
