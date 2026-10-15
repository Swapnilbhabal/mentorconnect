import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { api } from "../api";
import MentorNetwork from "./MentorNetwork";
import RoadmapPanel from "./RoadmapPanel";
import SessionList from "./SessionList";
import { ErrorNote, useAction } from "./ui";

export function SystemStatus() {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "down" }));
  }, []);

  if (!health) return null;
  const down = health.status !== "ok";
  const noAi = !down && !health.ai_configured;
  return (
    <p className={`status ${down ? "status-bad" : noAi ? "status-warn" : "status-ok"}`} role="status">
      <span className="dot" aria-hidden="true" />
      {down ? "Server unreachable" : noAi ? "Gemini key missing, templates only" : "All systems normal"}
    </p>
  );
}

/** Shared header + chrome for every student page. The actual page content renders via <Outlet/>,
 * so navigating between Roadmaps / Mentors / Sessions / Action Items / Profile is a real route
 * change -- no giant scrollable single page, no anchor-jumping. */
export default function StudentLayout({ user }) {
  return (
    <main className="hub">
      <header className="hub-head panel">
        <div>
          <h1>Welcome to the Hub, {user.full_name.split(" ")[0]}.</h1>
          <p className="muted">Plan your path with AI, then book time with the professors who can help.</p>
        </div>
        <SystemStatus />
      </header>
      <Outlet />
    </main>
  );
}

export function RoadmapsPage() {
  return <RoadmapPanel />;
}

export function MentorsPage() {
  return <MentorNetwork onBooked={() => {}} />;
}

export function SessionsPage() {
  const [bookings, setBookings] = useState([]);
  const refresh = () => api.bookings().then(setBookings).catch(() => {});
  useEffect(() => { refresh(); }, []);
  return <SessionList role="student" bookings={bookings} onChange={refresh} />;
}

export function StudentProfilePage() {
  const [form, setForm] = useState(null);
  const [saved, setSaved] = useState(false);
  const action = useAction();

  useEffect(() => {
    api.myStudentProfile().then((p) => {
      setForm({
        institute_type: p.institute_type || "",
        institute_name: p.institute_name || "",
        roll_number: p.roll_number || "",
        program_level: p.program_level || "",
        year_of_study: p.year_of_study || "",
        branch: p.branch || "",
      });
    }).catch((e) => action.setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = (k) => (e) => { setForm((f) => ({ ...f, [k]: e.target.value })); setSaved(false); };

  async function submit(e) {
    e.preventDefault();
    const updated = await action.run(() =>
      api.updateStudentProfile({
        ...form,
        institute_type: form.institute_type || null,
        institute_name: form.institute_type ? form.institute_name : null,
        program_level: form.program_level || null,
      })
    );
    if (updated) setSaved(true);
  }

  if (!form) return null;

  return (
    <section className="panel" aria-labelledby="student-profile-title">
      <h2 id="student-profile-title" className="panel-title">My profile</h2>
      <p className="panel-sub">Your academic details -- shared context for mentors, editable anytime.</p>
      <form onSubmit={submit} className="stack">
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
            <label className="field grow">
              <span>Institute name</span>
              <input className="input" required value={form.institute_name} onChange={set("institute_name")} placeholder="e.g., VIT Vellore" />
            </label>
          )}
        </div>
        <div className="row row-wrap">
          <label className="field grow"><span>Roll number</span><input className="input" value={form.roll_number} onChange={set("roll_number")} placeholder="e.g., 21BCE1234" /></label>
          <label className="field">
            <span>Program level</span>
            <select className="input" value={form.program_level} onChange={set("program_level")}>
              <option value="">Not specified</option>
              <option value="UG">Undergraduate</option>
              <option value="PG">Postgraduate</option>
            </select>
          </label>
          <label className="field"><span>Year of study</span><input className="input" value={form.year_of_study} onChange={set("year_of_study")} placeholder="e.g., 2nd Year" /></label>
        </div>
        <label className="field"><span>Branch / major</span><input className="input" value={form.branch} onChange={set("branch")} placeholder="e.g., Computer Science" /></label>
        <ErrorNote>{action.error}</ErrorNote>
        <div className="row row-end">
          {saved && <span className="ok-text" role="status">Profile saved</span>}
          <button className="btn btn-primary" disabled={action.busy}>{action.busy ? "Saving…" : "Save profile"}</button>
        </div>
      </form>
    </section>
  );
}