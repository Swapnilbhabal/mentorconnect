import { useState } from "react";

export function Avatar({ name = "", src, size = 48 }) {
  const [failed, setFailed] = useState(false);
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  const style = { width: size, height: size, fontSize: size * 0.36 };

  if (!src || failed) {
    return (
      <span className="avatar avatar-fallback" style={style} aria-hidden="true">
        {initials || "?"}
      </span>
    );
  }
  return <img className="avatar" style={style} src={src} alt="" onError={() => setFailed(true)} loading="lazy" />;
}

export function RatingBadge({ rating, count }) {
  if (rating == null) {
    return (
      <span className="score score-new" title="This mentor has no ratings yet">
        <span className="score-value">New</span>
      </span>
    );
  }
  const pct = (rating / 5) * 100;
  const reviews = count ? `, from ${count} review${count === 1 ? "" : "s"}` : "";
  return (
    <span
      className="score"
      style={{ "--pct": `${pct}%` }}
      title={`${rating.toFixed(1)} out of 5${reviews}`}
      aria-label={`Rating ${rating.toFixed(1)} out of 5${reviews}`}
    >
      <span className="score-value">{rating.toFixed(1)}</span>
    </span>
  );
}

export const MODE_LABELS = { meet: "Video Call (Zoom)", teams: "Microsoft Teams", offline: "On campus" };

export const VERIFICATION_PATH_LABELS = {
  industry: "Industry Professional",
  academic: "Academic Mentor",
  coaching: "Coaching Teacher",
  community: "Community Mentor",
};

export function VerifiedBadge({ verified, size = "sm" }) {
  if (!verified) return null;
  return (
    <span className={`verified-badge verified-badge-${size}`} title="Approved by a platform admin">
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="9" fill="currentColor" />
        <path d="M6 10.2l2.5 2.5L14.5 7" stroke="var(--panel-solid, #0b1120)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Platform Verified
    </span>
  );
}

// Mentor slots are stored as (weekday, HH:MM) in UTC. This converts them into the viewer's
// own local time for display, so nobody has to do UTC math in their head to book correctly.
// Uses Jan 1 2024 (a known Monday) purely as a reference date -- only the weekday/time-of-day
// after local conversion is used, not the actual date.
const REF_MONDAY_UTC_MS = Date.UTC(2024, 0, 1);

export function slotToLocalLabel(slot) {
  const [sh, sm] = slot.start_time.split(":").map(Number);
  const [eh, em] = slot.end_time.split(":").map(Number);
  const start = new Date(REF_MONDAY_UTC_MS + slot.weekday * 86_400_000 + (sh * 60 + sm) * 60_000);
  const end = new Date(REF_MONDAY_UTC_MS + slot.weekday * 86_400_000 + (eh * 60 + em) * 60_000);
  const fmtDay = (d) => d.toLocaleDateString(undefined, { weekday: "long" });
  const fmtTime = (d) => d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  const startDay = fmtDay(start);
  const endDay = fmtDay(end);
  return startDay === endDay
    ? `${startDay} ${fmtTime(start)}\u2013${fmtTime(end)}`
    : `${startDay} ${fmtTime(start)} \u2013 ${endDay} ${fmtTime(end)}`;
}

export function slotsToLocalSummary(slots) {
  if (!slots || slots.length === 0) return null;
  return slots.map(slotToLocalLabel).join(", ");
}

// Same UTC->local conversion as slotToLocalLabel, but returns the raw parts (weekday +
// minute-of-day) instead of a formatted string -- used by the color-coded slot picker to
// check "is this exact local moment inside one of the mentor's declared windows."
export function utcSlotToLocalParts(slot) {
  const [sh, sm] = slot.start_time.split(":").map(Number);
  const [eh, em] = slot.end_time.split(":").map(Number);
  const start = new Date(REF_MONDAY_UTC_MS + slot.weekday * 86_400_000 + (sh * 60 + sm) * 60_000);
  const end = new Date(REF_MONDAY_UTC_MS + slot.weekday * 86_400_000 + (eh * 60 + em) * 60_000);
  const localWeekday = (start.getDay() + 6) % 7;
  const endWeekday = (end.getDay() + 6) % 7;
  return {
    weekday: localWeekday,
    endWeekday,
    startMinutes: start.getHours() * 60 + start.getMinutes(),
    endMinutes: end.getHours() * 60 + end.getMinutes(),
  };
}
export function formatWhen(iso) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function ErrorNote({ children }) {
  if (!children) return null;
  return (
    <p className="note note-error" role="alert">
      {children}
    </p>
  );
}

export function useAction() {
  // Runs an async action, tracking its busy/error state.
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      return await fn();
    } catch (e) {
      setError(e.message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, setError, run };
}