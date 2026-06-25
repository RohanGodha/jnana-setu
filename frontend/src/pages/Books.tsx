import { NavBar } from "../components/NavBar";
import { BookGrid } from "../components/BookGrid";

export function Books() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <h1 className="mb-4 font-display text-3xl text-text-primary">The Library</h1>
        <BookGrid />
      </main>
    </div>
  );
}
