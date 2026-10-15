import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { Avatar, ErrorNote, MODE_LABELS, slotToLocalLabel, useAction, utcSlotToLocalParts } from "./ui";

function todayStr() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const WEEKDAY_HEADS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

/** A real visual month-grid calendar dropdown -- click the trigger to open a month view with
 * prev/next navigation, weekday headers, and a grid of day cells; past dates are disabled.
 * Replaces the native date input, which allowed typing garbage straight into the year field. */
function CalendarPicker({ dateStr, onChange }) {
  const wrapRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [viewDate, setViewDate] = useState(() => {
    const [y, m] = dateStr.split("-").map(Number);
    return new Date(y, m - 1, 1);
  });

  useEffect(() => {
    function onOutside(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  const today = useMemo(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }, []);
  const [sy, sm, sd] = dateStr.split("-").map(Number);
  const selected = new Date(sy, sm - 1, sd);

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const startOffset = (new Date(year, month, 1).getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [...Array(startOffset).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];

  const pad = (n) => String(n).padStart(2, "0");
  function pick(d) {
    onChange(`${year}-${pad(month + 1)}-${pad(d)}`);
    setOpen(false);
  }

  return (
    <div className="cal-picker" ref={wrapRef}>
      <button type="button" className="input cal-trigger" onClick={() => setOpen((o) => !o)}>
        {selected.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" })}
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="cal-popover" role="dialog" aria-label="Choose a date">
          <div className="cal-header">
            <button type="button" className="cal-nav" onClick={() => setViewDate(new Date(year, month - 1, 1))} aria-label="Previous month">‹</button>
            <strong>{viewDate.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</strong>
            <button type="button" className="cal-nav" onClick={() => setViewDate(new Date(year, month + 1, 1))} aria-label="Next month">›</button>
          </div>
          <div className="cal-weekdays">{WEEKDAY_HEADS.map((w) => <span key={w}>{w}</span>)}</div>
          <div className="cal-grid">
            {cells.map((d, i) => {
              if (d === null) return <span key={i} className="cal-cell cal-empty" />;
              const cellDate = new Date(year, month, d);
              const isPast = cellDate < today;
              const isSelected = cellDate.getTime() === selected.getTime();
              return (
                <button
                  key={i} type="button" disabled={isPast}
                  className={`cal-cell ${isSelected ? "cal-selected" : ""}`}
                  onClick={() => pick(d)}
                >
                  {d}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function isWithinMentorHours(localParts, weekday, minutesOfDay) {
  return localParts.some(
    (p) => p.weekday === weekday && p.weekday === p.endWeekday && minutesOfDay >= p.startMinutes && minutesOfDay < p.endMinutes
  );
}

/** Pick a date with a real calendar dropdown, then see that day's slots color-coded: green =
 * free and within the mentor's hours, red = already booked by someone (no identity shown, just
 * "taken"), gray = outside the mentor's declared hours. This is a visual aid only -- the server
 * is still the final word on whether a specific request actually succeeds, same as the
 * availability-enforcement it's built from. */
function SlotPicker({ mentor, busy, value, onChange }) {
  const [dateStr, setDateStr] = useState(todayStr);
  const mentorHasSlots = mentor.slots && mentor.slots.length > 0;
  const localParts = useMemo(() => (mentorHasSlots ? mentor.slots.map(utcSlotToLocalParts) : []), [mentor.slots]);

  const [y, mo, d] = dateStr.split("-").map(Number);
  const selectedDay = new Date(y, mo - 1, d);
  const dayWeekday = (selectedDay.getDay() + 6) % 7; // 0=Mon..6=Sun

  let rangeStart = 8 * 60;
  let rangeEnd = 20 * 60;
  if (mentorHasSlots) {
    const today = localParts.filter((p) => p.weekday === dayWeekday && p.weekday === p.endWeekday);
    if (today.length) {
      rangeStart = Math.max(0, Math.min(...today.map((p) => p.startMinutes)) - 60);
      rangeEnd = Math.min(24 * 60, Math.max(...today.map((p) => p.endMinutes)) + 60);
    } else {
      rangeStart = 9 * 60;
      rangeEnd = 18 * 60;
    }
  }

  const now = new Date();
  const slots = [];
  for (let m = rangeStart; m < rangeEnd; m += 30) {
    const start = new Date(selectedDay.getFullYear(), selectedDay.getMonth(), selectedDay.getDate(), 0, m);
    if (start <= now) continue;
    const end = new Date(start.getTime() + 30 * 60_000);
    const isBusy = busy.some((b) => start < new Date(b.end) && end > new Date(b.start));
    const inHours = !mentorHasSlots || isWithinMentorHours(localParts, dayWeekday, m);
    const state = isBusy ? "red" : inHours ? "green" : "gray";
    slots.push({ start, state });
  }

  const fmtTime = (d) => d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });

  return (
    <div className="slot-picker">
      <div className="field" style={{ maxWidth: "260px" }}>
        <span>Pick a date</span>
        <CalendarPicker dateStr={dateStr} onChange={setDateStr} />
      </div>
      <div className="slot-legend">
        <span><i className="slot-dot slot-dot-green" /> Available</span>
        <span><i className="slot-dot slot-dot-red" /> Already booked</span>
        {mentorHasSlots && <span><i className="slot-dot slot-dot-gray" /> Outside mentor's hours</span>}
      </div>
      <div className="slot-grid">
        {slots.length === 0 && <p className="muted small">No times left to show for this day.</p>}
        {slots.map(({ start, state }) => {
          const selected = value && start.getTime() === value.getTime();
          const label = state === "red" ? "Already booked" : state === "gray" ? "Outside mentor's usual hours" : "Available";
          return (
            <button
              key={start.toISOString()}
              type="button"
              disabled={state !== "green"}
              aria-pressed={selected}
              className={`slot-btn slot-${state} ${selected ? "slot-selected" : ""}`}
              onClick={() => onChange(start)}
              title={label}
            >
              {fmtTime(start)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function BookingDialog({ mentor, onClose, onBooked }) {
  const ref = useRef(null);
  const [mode, setMode] = useState(mentor.available_modes[0]);
  const [when, setWhen] = useState(null);
  const [duration, setDuration] = useState(30);
  const [topic, setTopic] = useState("");
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState([]);
  const [busyLoaded, setBusyLoaded] = useState(false);
  const action = useAction();

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  useEffect(() => {
    api.mentorBusy(mentor.id)
      .then((rows) => setBusy(rows.map((r) => ({ start: r.start, end: r.end }))))
      .catch(() => setBusy([]))
      .finally(() => setBusyLoaded(true));
  }, [mentor.id]);

  async function submit(e) {
    e.preventDefault();
    if (!when) return action.setError("Pick a time above first.");
    const booking = await action.run(() =>
      api.createBooking({
        mentor_id: mentor.id,
        scheduled_at: when.toISOString(),
        duration_minutes: Number(duration),
        mode,
        topic,
      })
    );
    if (booking) {
      setDone(booking);
      onBooked();
    }
  }

  return (
    <dialog ref={ref} className="dialog dialog-wide" onClose={onClose} aria-labelledby="book-title">
      <div className="dialog-head">
        <Avatar name={mentor.name} src={mentor.avatar_url} size={44} />
        <div>
          <h3 id="book-title">Book {mentor.name}</h3>
          {mentor.slots && mentor.slots.length > 0 ? (
            <p className="muted small">
              Available (your time zone): {mentor.slots.map((s) => slotToLocalLabel(s)).join(", ")}
            </p>
          ) : mentor.availability ? (
            <p className="muted small">Usually available {mentor.availability} (mentor's own words, not enforced)</p>
          ) : null}
        </div>
      </div>

      {done ? (
        <div className="dialog-done">
          <p><strong>Request sent.</strong> {mentor.name} will confirm your session.</p>
          {done.meeting_link && (
            <p className="small">Your {MODE_LABELS[done.mode]} room: <a href={done.meeting_link} target="_blank" rel="noreferrer">{done.meeting_link}</a></p>
          )}
          {done.mode === "offline" && (
            done.location
              ? <p className="small">Meet at {done.location}.</p>
              : <p className="small muted">Room to be confirmed by {mentor.name} -- you'll see it here and get a notification once it's set.</p>
          )}
          <button className="btn btn-primary" onClick={() => ref.current.close()}>Close</button>
        </div>
      ) : (
        <form onSubmit={submit} className="stack">
          <fieldset className="fieldset">
            <legend>How do you want to meet?</legend>
            <div className="radio-row">
              {mentor.available_modes.map((m) => (
                <label key={m} className={`radio ${mode === m ? "on" : ""}`}>
                  <input type="radio" name="mode" value={m} checked={mode === m} onChange={() => setMode(m)} />
                  {MODE_LABELS[m]}
                </label>
              ))}
            </div>
            {mode === "offline" && (
              <p className="muted small" style={{ marginTop: "0.4rem" }}>
                {mentor.campus_location
                  ? `Usually meets at ${mentor.campus_location} (${mentor.name} can adjust this per session).`
                  : `${mentor.name} hasn't set a default room yet -- they'll confirm the exact room after accepting your request.`}
              </p>
            )}
          </fieldset>

          <div className="field">
            <span>Date and time (your local time zone)</span>
            {!busyLoaded ? (
              <p className="muted small">Loading availability…</p>
            ) : (
              <SlotPicker mentor={mentor} busy={busy} value={when} onChange={setWhen} />
            )}
            {when && (
              <p className="small" style={{ marginTop: "0.5rem" }}>
                Selected: {when.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" })} at{" "}
                {when.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
              </p>
            )}
          </div>

          <label className="field">
            <span>Length</span>
            <select className="input" style={{ maxWidth: "200px" }} value={duration} onChange={(e) => setDuration(e.target.value)}>
              {[15, 30, 45, 60].map((d) => <option key={d} value={d}>{d} minutes</option>)}
            </select>
          </label>

          <label className="field">
            <span>What would you like help with?</span>
            <textarea className="input" rows={3} maxLength={300} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g., Review my capstone project plan" />
          </label>

          <ErrorNote>{action.error}</ErrorNote>
          <div className="row row-end">
            <button type="button" className="btn btn-ghost" onClick={() => ref.current.close()}>Cancel</button>
            <button className="btn btn-primary" disabled={action.busy || !when}>{action.busy ? "Booking…" : "Request session"}</button>
          </div>
        </form>
      )}
    </dialog>
  );
}