const API_BASE = "http://localhost:8000";

async function j(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export const api = {
  news: () => j(`${API_BASE}/api/news`),
  newsDetail: (id) => j(`${API_BASE}/api/news/${id}`),
  users: () => j(`${API_BASE}/api/users`),
  setBio: (id, bio) =>
    j(`${API_BASE}/api/users/${id}/bio`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bio }),
    }),
  bookmarks: (id) => j(`${API_BASE}/api/users/${id}/bookmarks`),
  setBookmark: (id, mid, on) =>
    j(`${API_BASE}/api/users/${id}/bookmarks/${mid}`, { method: on ? "PUT" : "DELETE" }),
  recommendations: (id, k = 6) =>
    j(`${API_BASE}/api/recommendations?user_id=${id}&k=${k}`),
  settings: (id) => j(`${API_BASE}/api/users/${id}/settings`),
  saveSettings: (id, body) =>
    j(`${API_BASE}/api/users/${id}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  schedule: (id, from, to) =>
    j(`${API_BASE}/api/schedule?user_id=${id}&from=${from}&to=${to}`),
};
