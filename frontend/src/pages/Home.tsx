import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Library } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { KnowledgeLine } from "../components/KnowledgeLine";
import { DailyReflection } from "../components/DailyReflection";

export function Home() {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const ask = () => {
    const q = query.trim();
    navigate("/chat", { state: q ? { initialQuery: q } : undefined });
  };

  return (
    <div className="min-h-screen">
      <KnowledgeLine />
      <NavBar />

      <main className="mx-auto max-w-3xl px-4 py-16">
        <div className="text-center">
          <h1 className="font-display text-4xl leading-tight text-text-primary sm:text-5xl">
            A bridge to 600 years of
            <span className="text-accent"> Jain wisdom</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-text-secondary">
            Ask any question and receive answers drawn directly from canonical Digambar
            scriptures and the works of eleven contemporary Acharyas — every claim cited
            to its source.
          </p>
        </div>

        <div className="mt-10">
          <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-surface p-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask()}
              placeholder="Ask the library…  e.g. What is the nature of the soul?"
              className="flex-1 bg-transparent px-3 py-2 text-text-primary placeholder:text-text-secondary focus:outline-none"
            />
            <button
              onClick={ask}
              className="flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-bg hover:brightness-110"
            >
              Ask <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="mt-10">
          <DailyReflection />
        </div>

        <div className="mt-8 text-center">
          <button
            onClick={() => navigate("/books")}
            className="inline-flex items-center gap-2 text-sm text-accent hover:underline"
          >
            <Library className="h-4 w-4" /> Explore the library →
          </button>
        </div>
      </main>
    </div>
  );
}
