import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { SystemStatus } from "./StudentHub";
import { Avatar, ErrorNote, useAction } from "./ui";

const TABS = [
  { value: "pending", label: "Pending review" },
  { value: "verified", label: "Verified" },
  { value: "rejected", label: "Rejected" },
  { value: "unverified", label: "Not submitted" },
];

function RejectForm({ mentorId, onDone }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const action = useAction();

  if (!open) {
    return <button className="btn btn-ghost btn-sm" onClick={() => setOpen(true)}>Reject</button>;
  }

  async function submit(e) {
    e.preventDefault();
    const ok = await action.run(async () => {
      await api.adminReject(mentorId, reason);
      return true;
    });
    if (ok) onDone();
  }

  return (
    <form className="reject-form" onSubmit={submit}>
      <label className="field grow">
        <span>Reason for rejection</span>
        <input className="input" required value={reason} maxLength={1000} onChange={(e) => setReason(e.target.value)} placeholder="e.g., Document is blurry, please re-upload" />
      </label>
      <button className="btn btn-sm" disabled={action.busy}>{action.busy ? "Rejecting…" : "Confirm reject"}</button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setOpen(false)}>Cancel</button>
      <ErrorNote>{action.error}</ErrorNote>
    </form>
  );
}

function QueueItem({ item, showActions, onChange }) {
  const action = useAction();

  async function approve() {
    const ok = await action.run(async () => {
      await api.adminApprove(item.mentor_id);
      return true;
    });
    if (ok) onChange();
  }

  async function download() {
    await action.run(() => api.adminDownloadDocument(item.mentor_id, item.document_name));
  }

  return (
    <li className="admin-item">
      <div className="admin-item-top">
        <div>
          <h4>{item.name}</h4>
          <p className="muted small">{[item.department, item.path_label].filter(Boolean).join(" · ")}</p>
          <p className="small">{item.expertise}</p>
        </div>
        <span className={`pill pill-${item.status}`}>{item.status}</span>
      </div>

      {item.document_name && (
        <p className="small" style={{ marginTop: "0.5rem" }}>
          Document: <button className="link-btn" style={{ marginBottom: 0 }} disabled={action.busy} onClick={download}>
            {item.document_name}
          </button>
        </p>
      )}

      {showActions && (
        <div className="admin-item-actions">
          <button className="btn btn-primary btn-sm" disabled={action.busy} onClick={approve}>
            {action.busy ? "Working…" : "Approve"}
          </button>
          <RejectForm mentorId={item.mentor_id} onDone={onChange} />
        </div>
      )}
      <ErrorNote>{action.error}</ErrorNote>
    </li>
  );
}

export default function AdminHub({ user }) {
  const [tab, setTab] = useState("pending");
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    setItems(null);
    api.adminVerifications(tab).then(setItems).catch((e) => setError(e.message));
  }, [tab]);
  useEffect(refresh, [refresh]);

  return (
    <main className="hub">
      <header className="hub-head panel">
        <div className="row">
          <Avatar name={user.full_name} src={user.avatar_url} size={56} />
          <div>
            <h1>Welcome, {user.full_name}.</h1>
            <p className="muted">Review mentor credentials and manage Platform Verified status.</p>
          </div>
        </div>
        <SystemStatus />
      </header>

      <section className="panel" id="verifications" aria-labelledby="verifications-title">
        <h2 id="verifications-title" className="panel-title">Mentor verification queue</h2>
        <p className="panel-sub">Approving a mentor immediately shows the Platform Verified badge on their public profile.</p>

        <div className="tabs" role="tablist" aria-label="Filter by status">
          {TABS.map((t) => (
            <button
              key={t.value}
              role="tab"
              aria-selected={tab === t.value}
              className={`chip chip-btn ${tab === t.value ? "chip-on" : ""}`}
              onClick={() => setTab(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <ErrorNote>{error}</ErrorNote>
        {items === null && !error && <p className="empty">Loading…</p>}
        {items?.length === 0 && <p className="empty">No mentors in this category right now.</p>}

        {items?.length > 0 && (
          <ul className="admin-queue">
            {items.map((item) => (
              <QueueItem key={item.mentor_id} item={item} showActions={tab === "pending"} onChange={refresh} />
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}