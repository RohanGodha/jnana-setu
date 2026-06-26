import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Check, Crown } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { useAuth } from "../hooks/useAuth";
import { createOrder, fetchPlan, submitPayment } from "../api/endpoints";
import type { PlanInfo, UpiOrder } from "../types";

export function Pro() {
  const { user } = useAuth();
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [order, setOrder] = useState<UpiOrder | null>(null);
  const [txn, setTxn] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPlan().then(setPlan).catch(() => {});
  }, []);

  const hasAccess = user?.is_admin || user?.is_pro;

  const startOrder = async () => {
    setBusy(true);
    setError("");
    try {
      setOrder(await createOrder());
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Could not create order.");
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!order || !txn.trim()) return;
    setBusy(true);
    setError("");
    try {
      await submitPayment(order.payment_id, txn.trim());
      setDone(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Submit failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />
      <main className="mx-auto max-w-2xl px-4 py-12">
        <div className="flex items-center gap-3">
          <Crown className="h-7 w-7 text-accent" />
          <h1 className="font-display text-3xl text-text-primary">Jnana Setu Pro</h1>
        </div>

        {!user && (
          <p className="mt-6 text-text-secondary">
            Please <Link to="/login" className="text-accent hover:underline">sign in</Link> to upgrade.
          </p>
        )}

        {user && hasAccess && (
          <div className="mt-8 rounded-2xl border border-accent/30 bg-surface p-6">
            <p className="flex items-center gap-2 text-lg text-text-primary">
              <Check className="h-5 w-5 text-green-400" />
              {user.is_admin ? "You have admin access — everything unlocked." : "You're a Pro member 🎉"}
            </p>
            {user.pro_until && !user.is_admin && (
              <p className="mt-2 text-sm text-text-secondary">Valid until {new Date(user.pro_until).toLocaleDateString()}</p>
            )}
          </div>
        )}

        {user && !hasAccess && plan && (
          <div className="mt-8 grid gap-6">
            <div className="rounded-2xl border border-white/10 bg-surface p-6">
              <div className="flex items-baseline justify-between">
                <span className="text-text-primary">Pro plan</span>
                <span className="font-display text-3xl text-accent">₹{plan.price_inr}</span>
              </div>
              <p className="mt-1 text-sm text-text-secondary">{plan.days} days of full access</p>
              <ul className="mt-4 space-y-2">
                {plan.benefits.map((b) => (
                  <li key={b} className="flex items-center gap-2 text-sm text-text-secondary">
                    <Check className="h-4 w-4 text-accent" /> {b}
                  </li>
                ))}
              </ul>

              {!order && (
                <button
                  onClick={startOrder}
                  disabled={busy}
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-2.5 font-medium text-bg hover:brightness-110 disabled:opacity-50"
                >
                  {busy && <Loader2 className="h-4 w-4 animate-spin" />} Pay with UPI
                </button>
              )}
            </div>

            {order && !done && (
              <div className="rounded-2xl border border-white/10 bg-surface p-6">
                {!order.configured && (
                  <p className="mb-4 rounded-lg bg-yellow-500/10 p-3 text-sm text-yellow-300">
                    UPI is not configured by the admin yet. Showing a demo link.
                  </p>
                )}
                <p className="text-sm text-text-secondary">{order.instructions}</p>

                {order.qr_svg && (
                  <img
                    src={order.qr_svg}
                    alt="UPI QR"
                    className="mx-auto my-5 h-52 w-52 rounded-xl bg-white p-3"
                  />
                )}

                <a
                  href={order.upi_link}
                  className="block w-full rounded-xl border border-accent/40 py-2.5 text-center text-accent hover:bg-accent/10"
                >
                  Open UPI app — pay ₹{order.amount} to {order.vpa}
                </a>

                <div className="mt-6">
                  <label className="mb-1 block text-sm text-text-secondary">
                    After paying, enter your UPI transaction / reference ID
                  </label>
                  <input
                    value={txn}
                    onChange={(e) => setTxn(e.target.value)}
                    placeholder="e.g. 4163xxxxxxxx"
                    className="w-full rounded-xl border border-white/10 bg-bg px-4 py-2.5 text-text-primary focus:border-accent/50 focus:outline-none"
                  />
                  <button
                    onClick={submit}
                    disabled={busy || !txn.trim()}
                    className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-2.5 font-medium text-bg hover:brightness-110 disabled:opacity-50"
                  >
                    {busy && <Loader2 className="h-4 w-4 animate-spin" />} Submit payment
                  </button>
                </div>
              </div>
            )}

            {done && (
              <div className="rounded-2xl border border-green-500/30 bg-surface p-6 text-center">
                <Check className="mx-auto h-10 w-10 text-green-400" />
                <p className="mt-3 text-text-primary">Payment reference submitted!</p>
                <p className="mt-1 text-sm text-text-secondary">
                  Your Pro access unlocks once the admin verifies the payment.
                </p>
              </div>
            )}

            {error && <p className="text-sm text-red-400">{error}</p>}
          </div>
        )}
      </main>
    </div>
  );
}
