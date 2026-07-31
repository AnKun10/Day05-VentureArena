import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SettingsPage({ users, currentUser, onSelectUser }) {
  const [cohort, setCohort] = useState("3");
  const [ltRoom, setLtRoom] = useState("");
  const [labRoom, setLabRoom] = useState("");
  const [saved, setSaved] = useState(false);
  const settingsSeq = useRef(0);

  // Đổi user → nạp lại thiết lập của user đó (guard chống race khi đổi user liên tục)
  useEffect(() => {
    if (currentUser == null) return;
    const seq = ++settingsSeq.current;
    api
      .settings(currentUser)
      .then((s) => {
        if (seq !== settingsSeq.current) return;
        setCohort(s.cohort ?? "3");
        setLtRoom(s.lt_room ?? "");
        setLabRoom(s.lab_room ?? "");
      })
      .catch(() => {});
  }, [currentUser]);

  const handleSave = () => {
    if (currentUser == null) return;
    api
      .saveSettings(currentUser, { cohort, lt_room: ltRoom, lab_room: labRoom })
      .then(() => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      })
      .catch(() => {});
  };

  if (users === null || currentUser == null) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-6">
        <Card className="max-w-lg p-5 text-sm text-muted-foreground">
          Không thể kết nối tới máy chủ — tính năng Cài đặt tạm thời không khả dụng.
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-lg font-semibold">Cài đặt</h1>
          <p className="text-xs text-muted-foreground">
            Thiết lập khoá và lớp học dùng cho trang Lịch học và bot Discord
          </p>
        </div>
        <select
          className="h-8 rounded-lg border bg-background px-2 text-sm"
          value={currentUser ?? ""}
          onChange={(e) => onSelectUser(e.target.value)}
        >
          {users.map((u) => (
            <option key={u.user_id} value={u.user_id}>
              {u.name}
            </option>
          ))}
        </select>
      </div>

      <Card className="max-w-lg gap-4 p-5">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">Khoá</label>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={cohort === "3" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setCohort("3")}
            >
              Khoá 3
            </Button>
            <Button
              type="button"
              variant={cohort === "4" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setCohort("4")}
            >
              Khoá 4
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="settings-lt-room">
            Lớp Lý thuyết
          </label>
          <Input
            id="settings-lt-room"
            value={ltRoom}
            onChange={(e) => setLtRoom(e.target.value)}
            placeholder="VD: LT-01"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="settings-lab-room">
            Lớp Lab
          </label>
          <Input
            id="settings-lab-room"
            value={labRoom}
            onChange={(e) => setLabRoom(e.target.value)}
            placeholder="VD: LAB-01"
          />
        </div>

        <div className="flex items-center gap-3">
          <Button size="sm" onClick={handleSave}>
            Lưu
          </Button>
          {saved && <span className="text-xs text-primary">Đã lưu ✓</span>}
        </div>

        <p className="text-xs text-muted-foreground">
          Trang Lịch học và lệnh /schedule của bot trả theo thiết lập này.
        </p>
      </Card>
    </div>
  );
}
