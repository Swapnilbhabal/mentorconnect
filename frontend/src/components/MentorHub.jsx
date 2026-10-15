import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { api } from "../api";
import { SystemStatus } from "./StudentHub";
import SessionList from "./SessionList";
import { Avatar, ErrorNote, RatingBadge, useAction, VERIFICATION_PATH_LABELS, VerifiedBadge } from "./ui";

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

const ACCEPTED_TYPES = ".pdf,.jpg,.jpeg,.png";

export function VerificationPage() {
  const [verification, setVerification] = useState(null);
  const [path, setPath] = useState("industry");
  const [file, setFile] = useState(null);
  const action = useAction();

  useEffect(() => {
    api.myVerification().then(setVerification).catch((e) => action.setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(e) {
    e.preventDefault();
    if (!file) return action.setError("Choose a PDF, JPG or PNG file first.");
    const updated = await action.run(() => api.submitVerification(path, file));
    if (updated) {
      setVerification(updated);
      setFile(null);
      e.target.reset();
    }
  }

  if (!verification) return null;
  const canSubmit = verification.status === "unverified" || verification.status === "rejected";

  return (
    <section className="panel" aria-labelledby="verification-title">
      <h2 id="verification-title" className="panel-title">Platform verification</h2>
      <p className="panel-sub">Upload one credential document to earn the Platform Verified badge students see on your profile.</p>

      <div className="verification-box">
        <div className="verification-status-row">
          <span className={`pill pill-${verification.status}`}>
            {verification.status === "unverified" && "Not submitted yet"}
            {verification.status === "pending" && "Pending admin review"}
            {verification.status === "verified" && "Verified"}
            {verification.status === "rejected" && "Rejected"}
          </span>
          {verification.platform_verified && <VerifiedBadge verified size="sm" />}
          {verification.path_label && <span className="muted small">Path: {verification.path_label}</span>}
        </div>

        {verification.status === "pending" && (
          <p className="small muted">
            "{verification.document_name}" is waiting for an admin to review it. You'll see the result here once it's checked.
          </p>
        )}
        {verification.status === "rejected" && (
          <p className="note note-error" role="alert">
            Rejected: {verification.rejection_reason || "No reason given."} You can fix the issue and resubmit below.
          </p>
        )}
        {verification.status === "verified" && (
          <p className="small muted">Reviewed by {verification.reviewed_by || "an admin"}. No further action needed.</p>
        )}

        {canSubmit && (
          <form onSubmit={submit} className="stack" style={{ marginTop: "0.9rem" }}>
            <fieldset className="fieldset">
              <legend>Verification path</legend>
              <div className="radio-row">
                {Object.entries(VERIFICATION_PATH_LABELS).map(([value, label]) => (
                  <label key={value} className={`radio ${path === value ? "on" : ""}`}>
                    <input type="radio" name="path" value={value} checked={path === value} onChange={() => setPath(value)} />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="field">
              <span>Credential document (PDF, JPG or PNG, max 5MB)</span>
              <input
                className="input"
                type="file"
                accept={ACCEPTED_TYPES}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <ErrorNote>{action.error}</ErrorNote>
            <div className="row row-end">
              <button className="btn btn-primary" disabled={action.busy}>
                {action.busy ? "Uploading…" : "Submit for review"}
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// The backend always stores/enforces slots in UTC (the only timezone-safe choice for a system
// with users in different regions). These two helpers do the conversion at the boundary, so the
// mentor only ever sees and edits their OWN local time (e.g. IST) -- never UTC.
const REF_2024_01_01 = { y: 2024, m: 0, d: 1 }; // a known Monday, used only as a stable anchor date

function utcSlotToLocal({ weekday, start_time, end_time }) {
  const [sh, sm] = start_time.split(":").map(Number);
  const [eh, em] = end_time.split(":").map(Number);
  const baseUtcMs = Date.UTC(REF_2024_01_01.y, REF_2024_01_01.m, REF_2024_01_01.d + weekday);
  const start = new Date(baseUtcMs + (sh * 60 + sm) * 60_000);
  const end = new Date(baseUtcMs + (eh * 60 + em) * 60_000);
  const pad = (n) => String(n).padStart(2, "0");
  return {
    weekday: (start.getDay() + 6) % 7, // JS getDay: 0=Sun..6=Sat -> convert to 0=Mon..6=Sun
    start_time: `${pad(start.getHours())}:${pad(start.getMinutes())}`,
    end_time: `${pad(end.getHours())}:${pad(end.getMinutes())}`,
  };
}

function localSlotToUtc({ weekday, start_time, end_time }) {
  const [sh, sm] = start_time.split(":").map(Number);
  const [eh, em] = end_time.split(":").map(Number);
  const base = new Date(REF_2024_01_01.y, REF_2024_01_01.m, REF_2024_01_01.d + weekday);
  const start = new Date(base); start.setHours(sh, sm, 0, 0);
  const end = new Date(base); end.setHours(eh, em, 0, 0);
  const pad = (n) => String(n).padStart(2, "0");
  return {
    weekday: (start.getUTCDay() + 6) % 7,
    start_time: `${pad(start.getUTCHours())}:${pad(start.getUTCMinutes())}`,
    end_time: `${pad(end.getUTCHours())}:${pad(end.getUTCMinutes())}`,
  };
}

export function AvailabilityPage() {
  const [slots, setSlots] = useState(null); // always held in LOCAL time in this component's state
  const [weekday, setWeekday] = useState(0);
  const [start, setStart] = useState("21:30");
  const [end, setEnd] = useState("23:30");
  const [saved, setSaved] = useState(false);
  const action = useAction();

  useEffect(() => {
    api.mySlots().then((rows) => setSlots(rows.map(utcSlotToLocal))).catch((e) => action.setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addRow() {
    setSaved(false);
    if (start >= end) return action.setError("Start time must be before end time.");
    action.setError("");
    setSlots((rows) => [...rows, { weekday, start_time: start, end_time: end }]);
  }

  function removeRow(i) {
    setSaved(false);
    setSlots((rows) => rows.filter((_, idx) => idx !== i));
  }

  async function save() {
    const updated = await action.run(() => api.replaceMySlots(slots.map(localSlotToUtc)));
    if (updated) {
      setSlots(updated.map(utcSlotToLocal));
      setSaved(true);
    }
  }

  if (slots === null) return null;

  return (
    <section className="panel" aria-labelledby="availability-title">
      <h2 id="availability-title" className="panel-title">Weekly availability</h2>
      <p className="panel-sub">
        {slots.length === 0
          ? "No slots set: students can currently book you at any future time. Add slots below (in your own local time) to restrict bookings to only these windows."
          : "Students can only book times that fall inside one of these windows. Shown here in your local time zone; students see them converted to theirs."}
      </p>

      {slots.length > 0 && (
        <ul className="chips" style={{ marginTop: 0 }}>
          {slots.map((s, i) => (
            <li key={i} className="chip" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
              {WEEKDAYS[s.weekday]} {s.start_time}–{s.end_time}
              <button
                type="button"
                onClick={() => removeRow(i)}
                aria-label={`Remove ${WEEKDAYS[s.weekday]} ${s.start_time}-${s.end_time}`}
                style={{ background: "none", border: 0, color: "inherit", cursor: "pointer", padding: 0, lineHeight: 1 }}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="row row-wrap" style={{ marginTop: "0.9rem" }}>
        <label className="field">
          <span>Day</span>
          <select className="input" value={weekday} onChange={(e) => { setWeekday(Number(e.target.value)); setSaved(false); }}>
            {WEEKDAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
          </select>
        </label>
        <label className="field">
          <span>From (your local time)</span>
          <input type="time" className="input" value={start} onChange={(e) => { setStart(e.target.value); setSaved(false); }} />
        </label>
        <label className="field">
          <span>To (your local time)</span>
          <input type="time" className="input" value={end} onChange={(e) => { setEnd(e.target.value); setSaved(false); }} />
        </label>
        <button type="button" className="btn btn-outline btn-sm" onClick={addRow}>Add window</button>
      </div>

      <ErrorNote>{action.error}</ErrorNote>
      <div className="row row-end" style={{ marginTop: "0.8rem" }}>
        {saved && <span className="ok-text" role="status">Availability saved</span>}
        <button className="btn btn-primary" disabled={action.busy} onClick={save}>
          {action.busy ? "Saving…" : "Save availability"}
        </button>
      </div>
    </section>
  );
}

const INSTITUTIONAL_TYPES = ["school", "college", "university"];

export function MentorProfilePage() {
  const [form, setForm] = useState(null);
  const [saved, setSaved] = useState(false);
  const action = useAction();

  useEffect(() => {
    api.myMentorProfile().then((profile) => {
      setForm({
        name: profile.name,
        department: profile.department || "",
        years_experience: profile.years_experience || 0,
        expertise: profile.expertise,
        bio: profile.bio,
        long_bio: profile.long_bio || "",
        availability: profile.availability || "",
        meet_link: profile.meet_link || "",
        teams_link: profile.teams_link || "",
        campus_location: profile.campus_location || "",
        institute_type: profile.institute_type || "",
        institute_name: profile.institute_name || "",
        institute_unique_id: profile.institute_unique_id || "",
      });
    }).catch((e) => action.setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = (k) => (e) => {
    setSaved(false);
    setForm((f) => ({ ...f, [k]: e.target.value }));
  };
  const needsUniqueId = form && INSTITUTIONAL_TYPES.includes(form.institute_type);

  async function submit(e) {
    e.preventDefault();
    const updated = await action.run(() =>
      api.updateMentorProfile({
        ...form,
        years_experience: Number(form.years_experience) || 0,
        institute_type: form.institute_type || null,
        institute_name: form.institute_type ? form.institute_name : null,
        institute_unique_id: needsUniqueId ? form.institute_unique_id : null,
      })
    );
    if (updated) setSaved(true);
  }

  if (!form) return null;

  return (
    <section className="panel" aria-labelledby="profile-title">
      <h2 id="profile-title" className="panel-title">My profile</h2>
      <p className="panel-sub">Students can only book the meeting types you fill in below.</p>
      <form onSubmit={submit} className="stack">
        <div className="row row-wrap">
          <label className="field grow"><span>Full name</span><input className="input" required minLength={2} value={form.name} onChange={set("name")} /></label>
          <label className="field grow"><span>Department</span><input className="input" value={form.department} onChange={set("department")} /></label>
          <label className="field"><span>Years of experience</span><input type="number" min={0} max={60} className="input" value={form.years_experience} onChange={set("years_experience")} /></label>
        </div>
        <label className="field"><span>Expertise (comma separated)</span><input className="input" value={form.expertise} onChange={set("expertise")} placeholder="FastAPI, React, System Design" /></label>
        <label className="field"><span>Short bio (shown on the mentor list)</span><textarea className="input" rows={2} value={form.bio} onChange={set("bio")} /></label>
        <label className="field"><span>Full bio (shown only on your detail page -- qualifications, experience, achievements)</span><textarea className="input" rows={5} value={form.long_bio} onChange={set("long_bio")} placeholder="Optional. If left blank, your short bio above is shown instead." /></label>
        <label className="field"><span>Availability</span><input className="input" value={form.availability} onChange={set("availability")} placeholder="Mon-Thu, 4-6 PM" /></label>
        <div className="row row-wrap">
          <label className="field grow">
            <span>Institute type</span>
            <select className="input" value={form.institute_type} onChange={set("institute_type")}>
              <option value="">Not applicable</option>
              <option value="school">School</option>
              <option value="college">College</option>
              <option value="university">University</option>
              <option value="other">Other</option>
            </select>
          </label>
          {form.institute_type && (
            <label className="field grow"><span>Institute name</span><input className="input" required value={form.institute_name} onChange={set("institute_name")} placeholder="e.g., VIT Vellore" /></label>
          )}
        </div>
        {needsUniqueId && (
          <label className="field"><span>Institute-issued unique ID</span><input className="input" required value={form.institute_unique_id} onChange={set("institute_unique_id")} placeholder="e.g., VITCMPN111" /></label>
        )}
        <div className="row row-wrap">
          <label className="field grow"><span>Fallback video link (used only if Zoom is unavailable)</span><input type="url" className="input" value={form.meet_link} onChange={set("meet_link")} placeholder="https://meet.google.com/… or any backup link" /></label>
          <label className="field grow"><span>Microsoft Teams link</span><input type="url" className="input" value={form.teams_link} onChange={set("teams_link")} placeholder="https://teams.microsoft.com/…" /></label>
        </div>
        <label className="field"><span>Default on-campus room (optional -- students can already request on-campus; you confirm the room per session)</span><input className="input" value={form.campus_location} onChange={set("campus_location")} placeholder="e.g., Block D, Room 101" /></label>        <ErrorNote>{action.error}</ErrorNote>
        <div className="row row-end">
          {saved && <span className="ok-text" role="status">Profile saved</span>}
          <button className="btn btn-primary" disabled={action.busy}>{action.busy ? "Saving…" : "Save profile"}</button>
        </div>
      </form>
    </section>
  );
}

export function MentorSessionsPage() {
  const [bookings, setBookings] = useState([]);
  const refresh = () => api.bookings().then(setBookings).catch(() => {});
  useEffect(() => { refresh(); }, []);
  return <SessionList role="mentor" bookings={bookings} onChange={refresh} title="Session requests" />;
}

/** Shared header + live stats for every mentor page; actual page content renders via <Outlet/>. */
export default function MentorLayout({ user }) {
  const [profile, setProfile] = useState(null);
  const [verification, setVerification] = useState(null);
  const [pending, setPending] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    api.myMentorProfile().then(setProfile).catch((e) => setError(e.message));
    api.myVerification().then(setVerification).catch((e) => setError(e.message));
    api.bookings().then((rows) => setPending(rows.filter((b) => b.status === "pending").length)).catch(() => {});
  }, []);

  return (
    <main className="hub">
      <header className="hub-head panel">
        <div className="row">
          <Avatar name={user.full_name} src={user.avatar_url} size={56} />
          <div>
            <div className="row" style={{ gap: "0.5rem" }}>
              <h1>Welcome back, {user.full_name}.</h1>
              {verification && <VerifiedBadge verified={verification.platform_verified} />}
            </div>
            <p className="muted">Confirm requests, run your sessions and keep your profile current.</p>
          </div>
        </div>
        <SystemStatus />
      </header>
      <ErrorNote>{error}</ErrorNote>

      {profile && (
        <section className="stats panel" aria-label="Your numbers">
          <div className="stat"><RatingBadge rating={profile.rating_avg} count={profile.rating_count} /><span className="stat-label">Rating</span></div>
          <Stat label="Reviews" value={profile.rating_count} />
          <Stat label="Sessions completed" value={profile.sessions_completed} />
          <Stat label="Requests waiting" value={pending} />
        </section>
      )}

      <Outlet />
    </main>
  );
}