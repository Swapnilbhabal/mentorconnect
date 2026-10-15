import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { formatWhen } from "./ui";

const POLL_MS = 20_000;

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const boxRef = useRef(null);

  const refreshCount = useCallback(() => {
    api.unreadCount().then((r) => setUnread(r.count)).catch(() => {});
  }, []);

  useEffect(() => {
    refreshCount();
    const timer = setInterval(refreshCount, POLL_MS);
    return () => clearInterval(timer);
  }, [refreshCount]);

  useEffect(() => {
    function onClickOutside(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      api.notifications().then(setItems).catch(() => {});
    }
  }

  async function markAllRead() {
    await api.markAllNotificationsRead().catch(() => {});
    setItems((rows) => rows.map((n) => ({ ...n, is_read: true })));
    setUnread(0);
  }

  async function openNotification(n) {
    if (!n.is_read) {
      api.markNotificationRead(n.id).catch(() => {});
      setItems((rows) => rows.map((r) => (r.id === n.id ? { ...r, is_read: true } : r)));
      setUnread((u) => Math.max(0, u - 1));
    }
  }

  return (
    <div className="bell-wrap" ref={boxRef}>
      <button className="btn btn-ghost btn-sm bell-btn" onClick={toggle} aria-haspopup="true" aria-expanded={open} aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}>
        <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18" aria-hidden="true">
          <path d="M10 2a5 5 0 0 0-5 5v2.6c0 .6-.2 1.1-.6 1.6L3 13.1c-.6.7-.1 1.9.9 1.9h12.2c1 0 1.5-1.2.9-1.9l-1.4-1.9a2.5 2.5 0 0 1-.6-1.6V7a5 5 0 0 0-5-5z" />
          <path d="M7.5 16a2.5 2.5 0 0 0 5 0h-5z" />
        </svg>
        {unread > 0 && <span className="bell-dot">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div className="bell-panel" role="dialog" aria-label="Notifications">
          <div className="bell-panel-head">
            <span>Notifications</span>
            {unread > 0 && <button className="link-btn" style={{ margin: 0 }} onClick={markAllRead}>Mark all read</button>}
          </div>
          {items.length === 0 ? (
            <p className="empty" style={{ margin: "0.8rem" }}>Nothing yet.</p>
          ) : (
            <ul className="bell-list">
              {items.map((n) => (
                <li key={n.id} className={`bell-item ${n.is_read ? "" : "bell-item-unread"}`} onClick={() => openNotification(n)}>
                  <p className="bell-title">{n.title}</p>
                  <p className="bell-body">{n.body}</p>
                  <p className="bell-time">{formatWhen(n.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}