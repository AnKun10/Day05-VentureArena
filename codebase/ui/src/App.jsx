import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import TopBar from "./components/TopBar.jsx";
import ChatWidget from "./components/ChatWidget.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";
import ResourcesPage from "./pages/ResourcesPage.jsx";
import NewsPage from "./pages/NewsPage.jsx";
import { CLASSES, PAGES } from "./config.js";

export default function App() {
  const [page, setPage] = useState("news");
  const [query, setQuery] = useState("");
  const [myClass, setMyClass] = useState(CLASSES[0]);
  const [chatOpen, setChatOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false); // drawer cho màn hình hẹp
  // mã buổi cần mở khi bấm citation trong chat / badge buổi ở trang Tài nguyên
  const [focusCode, setFocusCode] = useState(null);
  // câu hỏi được mồi sẵn vào chat (từ nút "Hỏi về buổi này")
  const [prefill, setPrefill] = useState(null);
  // số câu hỏi CỦA CHÍNH USER NÀY đang chờ TA — chỉ hiện khi thật sự có
  const [myQueue, setMyQueue] = useState(0);

  // Tìm kiếm luôn áp vào TRANG ĐANG MỞ. Đổi trang thì xoá query để không
  // còn cảnh "trang trống mà không hiểu vì sao" (bản cũ: ô search hiện ở
  // mọi trang nhưng chỉ Bản tin dùng, còn Tài nguyên có ô search thứ hai).
  function navigate(next) {
    setPage(next);
    setQuery("");
    setNavOpen(false);
  }

  function openSession(code) {
    if (!code) return;
    setFocusCode(code);
    setPage("calendar");
    setQuery("");
    setNavOpen(false);
  }

  function askAbout(question) {
    setPrefill({ question, at: Date.now() });
    setChatOpen(true);
  }

  // HAX #2 — citation không chỉ để đọc: bấm vào là nhảy tới đúng nguồn trên UI.
  const openCitation = (cit) => openSession(cit?.session_code);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setNavOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const meta = PAGES[page];

  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      {/* Drawer overlay (chỉ màn hình hẹp) */}
      {navOpen && (
        <button
          className="fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-[2px] lg:hidden"
          onClick={() => setNavOpen(false)}
          aria-label="Đóng menu"
        />
      )}

      <Sidebar
        page={page}
        onNavigate={navigate}
        onAskCompanion={() => setChatOpen(true)}
        myClass={myClass}
        myQueue={myQueue}
        open={navOpen}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          page={page}
          meta={meta}
          query={query}
          onQuery={setQuery}
          myClass={myClass}
          onClass={setMyClass}
          queueCount={myQueue}
          onOpenNav={() => setNavOpen(true)}
        />

        <main className="min-h-0 flex-1 overflow-y-auto">
          {page === "news" && (
            <NewsPage query={query} onAsk={askAbout} onOpenSession={openSession} />
          )}
          {page === "calendar" && (
            <CalendarPage
              query={query}
              myClass={myClass}
              focusCode={focusCode}
              onFocusHandled={() => setFocusCode(null)}
              onAskAbout={askAbout}
            />
          )}
          {page === "resources" && (
            <ResourcesPage query={query} onOpenSession={openSession} />
          )}
        </main>
      </div>

      <ChatWidget
        open={chatOpen}
        prefill={prefill}
        onToggle={() => setChatOpen((o) => !o)}
        onClose={() => setChatOpen(false)}
        onOpenCitation={openCitation}
        onEscalate={() => setMyQueue((q) => q + 1)}
      />
    </div>
  );
}
