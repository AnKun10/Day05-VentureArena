import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";
import ResourcesPage from "./pages/ResourcesPage.jsx";
import NewsPage from "./pages/NewsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import { api } from "@/lib/api";

export default function App() {
  const [page, setPage] = useState("calendar");
  const [users, setUsers] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  // Mount: nạp danh sách user. ?user= trên URL chọn sẵn user đó nếu có, else user đầu.
  useEffect(() => {
    api
      .users()
      .then((list) => {
        setUsers(list);
        if (list.length) {
          const param = new URLSearchParams(location.search).get("user");
          const match = list.find((u) => String(u.user_id) === param);
          setCurrentUser(match ? match.user_id : list[0].user_id);
        }
      })
      .catch(() => setUsers(null));
  }, []);

  // Nạp lại danh sách user (VD: sau khi sửa bio) mà không đụng tới currentUser đang chọn
  const refreshUsers = useCallback(() => {
    api.users().then(setUsers).catch(() => {});
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar page={page} onNavigate={setPage} users={users} currentUser={currentUser} />
      <main className="min-w-0 flex-1 overflow-y-auto">
        {page === "calendar" && <CalendarPage currentUser={currentUser} />}
        {page === "resources" && <ResourcesPage />}
        {page === "news" && (
          <NewsPage
            users={users}
            currentUser={currentUser}
            onSelectUser={setCurrentUser}
            refreshUsers={refreshUsers}
          />
        )}
        {page === "settings" && (
          <SettingsPage
            users={users}
            currentUser={currentUser}
            onSelectUser={setCurrentUser}
            refreshUsers={refreshUsers}
          />
        )}
      </main>
    </div>
  );
}
