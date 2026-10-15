import { useEffect, useState } from "react";
import { api } from "../api";
import { Avatar, ErrorNote, formatWhen, MODE_LABELS, useAction } from "./ui";

const STATUS_LABEL = {
  pending: "Waiting for confirmation",
  confirmed: "Confirmed",
  completed: "Completed",
  cancelled: "Cancelled",
};

function RateForm({ booking, onDone }) {
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState("");
  const action = useAction();

  async function submit(e) {
    e.preventDefault();
    const updated = await action.run(() => api.reviewBooking(booking.id, rating, feedback));
    if (updated) onDone();
  }

  return (
    <form className="rate" onSubmit={submit}>
      <label className="field">
        <span>Rate this session</span>
        <select className="input" value={rating} onChange={(e) => setRating(Number(e.target.value))}>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} out of 5</option>)}
        </select>
      </label>
      <label className="field grow">
        <span>Comment (optional)</span>
        <input className="input" value={feedback} maxLength={1000} onChange={(e) => setFeedback(e.target.value)} />
      </label>
      <button className="btn btn-primary btn-sm" disabled={action.busy}>Submit rating</button>
      <ErrorNote>{action.error}</ErrorNote>
    </form>
  );
}

function CancelForm({ booking, onDone, onCancel }) {
  const [reason, setReason] = useState("");
  const action = useAction();

  async function submit(e) {
    e.preventDefault();
    const updated = await action.run(() => api.setBookingStatus(booking.id, "cancelled", reason));
    if (updated) onDone();
  }

  return (
    <form className="reject-form" onSubmit={submit}>
      <label className="field grow">
        <span>Why is this session being cancelled?</span>
        <input className="input" required value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} placeholder="e.g., No longer available at this time" />
      </label>
      <button className="btn btn-sm" disabled={action.busy}>{action.busy ? "Cancelling…" : "Confirm cancel"}</button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>Back</button>
      <ErrorNote>{action.error}</ErrorNote>
    </form>
  );
}

function defaultRescheduleValue(iso) {
  const d = new Date(new Date(iso).getTime() + 24 * 3600 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function RescheduleForm({ booking, onDone, onCancel }) {
  const [when, setWhen] = useState(() => defaultRescheduleValue(booking.scheduled_at));
  const [reason, setReason] = useState("");
  const action = useAction();

  async function submit(e) {
    e.preventDefault();
    const updated = await action.run(() => api.rescheduleBooking(booking.id, new Date(when).toISOString(), reason));
    if (updated) onDone();
  }

  return (
    <form className="stack" onSubmit={submit} style={{ marginTop: "0.7rem" }}>
      <div className="row row-wrap">
        <label className="field grow">
          <span>New date and time</span>
          <input type="datetime-local" className="input" required value={when} onChange={(e) => setWhen(e.target.value)} />
        </label>
      </div>
      <label className="field">
        <span>Reason for rescheduling</span>
        <input className="input" required value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} placeholder="e.g., Clashes with an exam" />
      </label>
      <ErrorNote>{action.error}</ErrorNote>
      <div className="row">
        <button className="btn btn-primary btn-sm" disabled={action.busy}>{action.busy ? "Rescheduling…" : "Confirm new time"}</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>Back</button>
      </div>
    </form>
  );
}
function LocationEditor({ booking, onChange }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(booking.location || "");
  const action = useAction();

  async function save(e) {
    e.preventDefault();
    const updated = await action.run(() => api.updateBookingLocation(booking.id, value));
    if (updated) {
      setEditing(false);
      onChange();
    }
  }

  if (!editing) {
    return (
      <button className="link-btn" style={{ margin: 0 }} onClick={() => { setValue(booking.location || ""); setEditing(true); }}>
        {booking.location ? "Change room" : "Set room for this session"}
      </button>
    );
  }

  return (
    <form onSubmit={save} className="row row-wrap" style={{ marginTop: "0.3rem" }}>
      <input
        className="input" style={{ maxWidth: "260px" }} required maxLength={200}
        value={value} onChange={(e) => setValue(e.target.value)}
        placeholder="e.g., Block D, Room 102" autoFocus
      />
      <button className="btn btn-primary btn-sm" disabled={action.busy}>{action.busy ? "Saving…" : "Save"}</button>
      <button type="button" className="btn btn-outline btn-sm" onClick={() => setEditing(false)}>Cancel</button>
      <ErrorNote>{action.error}</ErrorNote>
    </form>
  );
}
/** After a session is completed, the mentor can add quick raw notes which Gemini turns into
 * structured Strengths / Weaknesses / Action items. Once added, both sides can see them here. */
function SessionNotesSection({ booking, role, onChange }) {
  const [notes, setNotes] = useState(null);
  const [adding, setAdding] = useState(false);
  const [feedback, setFeedback] = useState("");
  const action = useAction();

  useEffect(() => {
    if (booking.has_notes) {
      api.sessionNotes(booking.id).then(setNotes).catch(() => {});
    }
  }, [booking.id, booking.has_notes]);

  if (booking.status !== "completed") return null;

  async function submit(e) {
    e.preventDefault();
    const created = await action.run(() => api.addSessionNotes(booking.id, feedback));
    if (created) {
      setNotes(created);
      setAdding(false);
      onChange();
    }
  }

  if (!booking.has_notes) {
    if (role !== "mentor") return null; // only the mentor writes notes; the student just sees nothing until they exist
    if (!adding) {
      return (
        <button className="link-btn" style={{ margin: 0 }} onClick={() => setAdding(true)}>
          Add session notes
        </button>
      );
    }
    return (
      <form onSubmit={submit} className="stack" style={{ marginTop: "0.5rem" }}>
        <label className="field">
          <span>What happened in this session? (turned into structured notes automatically)</span>
          <textarea
            className="input" rows={3} required minLength={3} maxLength={3000}
            value={feedback} onChange={(e) => setFeedback(e.target.value)}
            placeholder="e.g., Reviewed their capstone proposal -- strong on the ML pipeline, but needs to firm up the evaluation metrics before the next review."
          />
        </label>
        <div className="row">
          <button className="btn btn-primary btn-sm" disabled={action.busy}>{action.busy ? "Saving…" : "Save notes"}</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAdding(false)}>Cancel</button>
        </div>
        <ErrorNote>{action.error}</ErrorNote>
      </form>
    );
  }

  if (!notes) return <p className="muted small">Loading notes…</p>;

  return (
    <div className="notes-box">
      {notes.error_message && (
        <p className="muted small">AI formatting wasn't available, so this is a simpler note: {notes.error_message}</p>
      )}
      {notes.strengths.length > 0 && (
        <div className="notes-group">
          <strong>Strengths</strong>
          <ul>{notes.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {notes.weaknesses.length > 0 && (
        <div className="notes-group">
          <strong>Areas to work on</strong>
          <ul>{notes.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {notes.action_items.length > 0 && (
        <div className="notes-group">
          <strong>Action items</strong>
          <ul>{notes.action_items.map((a, i) => <li key={i}>{a.item} <span className="muted small">(by {formatWhen(a.deadline)})</span></li>)}</ul>
        </div>
      )}
    </div>
  );
}

/** For a mentor with a CONFIRMED upcoming session: their own past sessions with this specific
 * student, if any -- never another mentor's notes. Silently renders nothing on a genuine first
 * meeting, so it never shows an awkward "no history" box for the common case. */
function StudentHistory({ booking }) {
  const [memory, setMemory] = useState(null);

  useEffect(() => {
    if (booking.status === "confirmed") {
      api.studentMemory(booking.student_id).then(setMemory).catch(() => {});
    }
  }, [booking.id, booking.status, booking.student_id]);

  if (!memory || memory.sessions.length === 0) return null;

  return (
    <details className="memory-box">
      <summary>
        You've met {memory.student_name} before ({memory.sessions.length} past session{memory.sessions.length > 1 ? "s" : ""})
      </summary>
      {memory.sessions.map((s, i) => (
        <div key={i} className="memory-session">
          <p className="small"><strong>{formatWhen(s.session_date)}</strong> -- {s.topic}</p>
          {s.weaknesses.length > 0 && <p className="muted small">Previously working on: {s.weaknesses.join(", ")}</p>}
          {s.action_items.length > 0 && (
            <p className="muted small">Action items given: {s.action_items.map((a) => a.item).join("; ")}</p>
          )}
        </div>
      ))}
    </details>
  );
}

function SessionRow({ booking, role, onChange }) {
  const action = useAction();
  const [mode, setMode] = useState(null); // null | "cancel" | "reschedule"
  const isPast = new Date(booking.scheduled_at) < new Date();
  // No webhook tells the app when a call actually ends -- this is just a time-based reminder,
  // never an automatic fact. Once the scheduled end time has passed and the mentor still hasn't
  // marked it completed, prompt clearly instead of leaving it silently stuck as "Confirmed".
  const hasEnded = new Date(booking.scheduled_at).getTime() + booking.duration_minutes * 60_000 < Date.now();
  const awaitingConfirmation = booking.status === "confirmed" && hasEnded;
  const other = role === "mentor" ? booking.student_name : booking.mentor_name;

  const setStatus = async (status) => {
    const updated = await action.run(() => api.setBookingStatus(booking.id, status));
    if (updated) onChange();
  };

  const active = booking.status === "pending" || booking.status === "confirmed";
  const done = () => { setMode(null); onChange(); };

  return (
    <li className={`session session-${booking.status}`}>
      <Avatar name={other} src={role === "student" ? booking.mentor_avatar_url : null} size={40} />
      <div className="session-main">
        <div className="session-top">
          <h4>{other}</h4>
          <span className={`pill pill-${booking.status}`}>{STATUS_LABEL[booking.status]}</span>
        </div>
        {role === "mentor" && booking.student_academic && (
          booking.student_academic.roll_number || booking.student_academic.branch || booking.student_academic.institute_name
        ) && (
          <p className="muted small">
            {[
              booking.student_academic.roll_number,
              booking.student_academic.branch,
              booking.student_academic.year_of_study && `Year ${booking.student_academic.year_of_study}`,
              booking.student_academic.institute_name,
            ].filter(Boolean).join(" \u00b7 ")}
          </p>
        )}
        <p className="small">
          {formatWhen(booking.scheduled_at)}, {booking.duration_minutes} min, {MODE_LABELS[booking.mode]}
          {booking.status === "cancelled" && booking.cancelled_by && ` (cancelled by ${booking.cancelled_by})`}
        </p>
        {booking.status === "cancelled" && booking.cancellation_reason && (
          <p className="muted small">Reason: {booking.cancellation_reason}</p>
        )}
        {booking.reschedule_count > 0 && (
          <p className="muted small">
            Rescheduled by {booking.rescheduled_by} from {formatWhen(booking.previous_scheduled_at)}. Reason: {booking.reschedule_reason}
          </p>
        )}
        {booking.topic && <p className="muted small">Topic: {booking.topic}</p>}
        {booking.location && <p className="small">Location: {booking.location}</p>}
        {role === "mentor" && booking.mode === "offline" && (booking.status === "pending" || booking.status === "confirmed") && (
          <LocationEditor booking={booking} onChange={onChange} />
        )}
        {role === "student" && booking.mode === "offline" && !booking.location && (booking.status === "pending" || booking.status === "confirmed") && (
          <p className="muted small">Room not set yet -- {booking.mentor_name} will confirm it before the session.</p>
        )}
        {booking.rating && <p className="muted small">Rated {booking.rating}/5{booking.feedback ? `: ${booking.feedback}` : ""}</p>}
        {role === "mentor" && <StudentHistory booking={booking} />}

        {awaitingConfirmation && role === "mentor" && (
          <p className="note note-error" role="status">
            This session's scheduled time has passed. Did it actually happen? Click "End session" below so {booking.student_name} can rate it.
          </p>
        )}
        {awaitingConfirmation && role === "student" && (
          <p className="muted small">Waiting for {booking.mentor_name} to confirm this session happened before you can rate it.</p>
        )}

        {mode === "cancel" ? (
          <CancelForm booking={booking} onDone={done} onCancel={() => setMode(null)} />
        ) : mode === "reschedule" ? (
          <RescheduleForm booking={booking} onDone={done} onCancel={() => setMode(null)} />
        ) : (
          <div className="session-actions">
            {booking.meeting_link && booking.status === "confirmed" && (
              <a className="btn btn-primary btn-sm" href={booking.meeting_link} target="_blank" rel="noreferrer">
                Join on {MODE_LABELS[booking.mode]}
              </a>
            )}
            {role === "mentor" && booking.status === "pending" && (
              <button className="btn btn-primary btn-sm" disabled={action.busy} onClick={() => setStatus("confirmed")}>Confirm</button>
            )}
            {role === "mentor" && booking.status === "confirmed" && isPast && (
              <button className="btn btn-primary btn-sm" disabled={action.busy} onClick={() => setStatus("completed")}>End session</button>
            )}
            {active && !isPast && (
              <button className="btn btn-ghost btn-sm" disabled={action.busy} onClick={() => setMode("reschedule")}>Reschedule</button>
            )}
            {active && (
              <button className="btn btn-ghost btn-sm" disabled={action.busy} onClick={() => setMode("cancel")}>Cancel</button>
            )}
          </div>
        )}
        <ErrorNote>{action.error}</ErrorNote>
        {role === "student" && booking.status === "completed" && !booking.rating && <RateForm booking={booking} onDone={onChange} />}
        <SessionNotesSection booking={booking} role={role} onChange={onChange} />
      </div>
    </li>
  );
}

export default function SessionList({ role, bookings, onChange, title = "My sessions" }) {
  // Unrated completed sessions get pulled into their own unmissable section at the top --
  // being buried in History was too easy to miss, and the point of this is you actually see it.
  const needsRating = role === "student" ? bookings.filter((b) => b.status === "completed" && !b.rating) : [];
  const needsRatingIds = new Set(needsRating.map((b) => b.id));
  const upcoming = bookings.filter((b) => b.status === "pending" || b.status === "confirmed").sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));
  const history = bookings.filter((b) => (b.status === "completed" || b.status === "cancelled") && !needsRatingIds.has(b.id));

  return (
    <section className="panel" id="sessions" aria-labelledby="sessions-title">
      <h2 id="sessions-title" className="panel-title">{title}</h2>

      {bookings.length === 0 && (
        <p className="empty">
          {role === "student"
            ? "You haven't booked a session yet. Pick a mentor above to get started."
            : "No sessions yet. Students will appear here when they book you."}
        </p>
      )}

      {needsRating.length > 0 && (
        <>
          <h3 className="group-title group-title-highlight">Rate your recent sessions</h3>
          <ul className="session-list">
            {needsRating.map((b) => <SessionRow key={b.id} booking={b} role={role} onChange={onChange} />)}
          </ul>
        </>
      )}
      {upcoming.length > 0 && (
        <>
          <h3 className="group-title">{role === "mentor" ? "Requests and upcoming" : "Upcoming"}</h3>
          <ul className="session-list">
            {upcoming.map((b) => <SessionRow key={b.id} booking={b} role={role} onChange={onChange} />)}
          </ul>
        </>
      )}
      {history.length > 0 && (
        <>
          <h3 className="group-title">History</h3>
          <ul className="session-list">
            {history.map((b) => <SessionRow key={b.id} booking={b} role={role} onChange={onChange} />)}
          </ul>
        </>
      )}
    </section>
  );
}