import { useChatStore } from "../store/chatStore";
import { ANUYOGA_CONFIG } from "./AnuyogaBadge";

const AUTHORS = [
  { slug: "all", label: "All sources" },
  { slug: "canonical", label: "Canonical texts" },
  { slug: "vidyasagar", label: "Acharya Vidyasagar Ji" },
  { slug: "vidyananda", label: "Acharya Vidyananda Ji" },
  { slug: "tarun_sagar", label: "Muni Tarun Sagar Ji" },
  { slug: "gyanmati", label: "Aryika Gyanmati Mataji" },
  { slug: "pushpadant_sagar", label: "Acharya Pushpadant Sagar Ji" },
  { slug: "deshbhushan", label: "Acharya Deshbhushan Ji" },
  { slug: "gupti_sagar", label: "Upadhyay Gupti Sagar Ji" },
  { slug: "vardhaman_sagar", label: "Acharya Vardhaman Sagar Ji" },
  { slug: "praman_sagar", label: "Muni Praman Sagar Ji" },
  { slug: "nirbhay_sagar", label: "Acharya Nirbhay Sagar Ji" },
  { slug: "pulak_sagar", label: "Pulak Sagar Ji" },
];

const ANUYOGAS = [
  { slug: "all_texts", label: "All categories" },
  { slug: "dravyanuyog", label: "Philosophy & Soul" },
  { slug: "charananuyog", label: "Ethics & Conduct" },
  { slug: "prathamanuyoga", label: "History & Lives" },
  { slug: "karnanuyoga", label: "Cosmology" },
];

export function AuthorFilter() {
  const authorFilter = useChatStore((s) => s.authorFilter);
  const setAuthorFilter = useChatStore((s) => s.setAuthorFilter);
  const anuyogaFilter = useChatStore((s) => s.anuyogaFilter);
  const setAnuyogaFilter = useChatStore((s) => s.setAnuyogaFilter);

  const toggleAuthor = (slug: string) => {
    if (slug === "all") {
      setAuthorFilter(["all"]);
      return;
    }
    let next = authorFilter.filter((a) => a !== "all");
    next = next.includes(slug) ? next.filter((a) => a !== slug) : [...next, slug];
    setAuthorFilter(next.length === 0 ? ["all"] : next);
  };

  return (
    <div className="space-y-6 text-sm">
      <section>
        <h3 className="mb-2 font-display text-base text-text-primary">Author</h3>
        <div className="space-y-1">
          {AUTHORS.map((a) => {
            const checked =
              a.slug === "all"
                ? authorFilter.includes("all")
                : authorFilter.includes(a.slug);
            return (
              <label
                key={a.slug}
                className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-white/5"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleAuthor(a.slug)}
                  className="h-3.5 w-3.5 accent-accent"
                />
                <span className={checked ? "text-text-primary" : "text-text-secondary"}>
                  {a.label}
                </span>
              </label>
            );
          })}
        </div>
      </section>

      <section>
        <h3 className="mb-2 font-display text-base text-text-primary">Anuyoga</h3>
        <div className="space-y-1">
          {ANUYOGAS.map((a) => {
            const active = anuyogaFilter === a.slug;
            const color = ANUYOGA_CONFIG[a.slug]?.color ?? "#8C8880";
            return (
              <button
                key={a.slug}
                onClick={() => setAnuyogaFilter(a.slug)}
                className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-white/5 ${
                  active ? "text-text-primary" : "text-text-secondary"
                }`}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: active ? color : "transparent", border: `1px solid ${color}` }}
                />
                {a.label}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
