import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Home } from "./pages/Home";
import { Chat } from "./pages/Chat";
import { Books } from "./pages/Books";
import { Login } from "./pages/Login";
import { Pro } from "./pages/Pro";
import { Bookmarks } from "./pages/Bookmarks";
import { Admin } from "./pages/Admin";
import { Explore } from "./pages/Explore";
import { Glossary } from "./pages/Glossary";
import { BookDetail } from "./pages/BookDetail";
import { Search } from "./pages/Search";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/books" element={<Books />} />
          <Route path="/books/:id" element={<BookDetail />} />
          <Route path="/search" element={<Search />} />
          <Route path="/login" element={<Login />} />
          <Route path="/pro" element={<Pro />} />
          <Route path="/bookmarks" element={<Bookmarks />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="/glossary" element={<Glossary />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
