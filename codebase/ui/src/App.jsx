import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";
import ResourcesPage from "./pages/ResourcesPage.jsx";
import NewsPage from "./pages/NewsPage.jsx";

export default function App() {
  const [page, setPage] = useState("calendar");

  return (
    <div className="flex h-screen overflow-hidden bg-[#0e1015]">
      <Sidebar page={page} onNavigate={setPage} />
      <main className="min-w-0 flex-1 overflow-y-auto">
        {page === "calendar" && <CalendarPage />}
        {page === "resources" && <ResourcesPage />}
        {page === "news" && <NewsPage />}
      </main>
    </div>
  );
}
