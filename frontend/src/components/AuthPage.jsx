import { useState } from "react";
import { api } from "../api";
import { ErrorNote, useAction } from "./ui";

const EMPTY_FORM = {
  full_name: "", email: "", password: "", role: "student", expertise: "",
  institute_type: "", institute_name: "",
  roll_number: "", program_level: "", year_of_study: "", branch: "",
  institute_unique_id: "",
};

const INSTITUTIONAL_TYPES = ["school", "college", "university"];

export default function AuthPage({ initialMode = "login", onAuthed, onBack }) {
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState(EMPTY_FORM);
  const action = useAction();
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const registering = mode === "register";
  const needsUniqueId = form.role === "mentor" && INSTITUTIONAL_TYPES.includes(form.institute_type);

  async function submit(e) {
    e.preventDefault();
    const res = await action.run(() =>
      registering
        ? api.register({
            email: form.email,
            password: form.password,
            full_name: form.full_name,
            role: form.role,
            expertise: form.role === "mentor" ? form.expertise || undefined : undefined,
            institute_type: form.institute_type || undefined,
            institute_name: form.institute_type ? form.institute_name : undefined,
            roll_number: form.role === "student" ? form.roll_number || undefined : undefined,
            program_level: form.role === "student" ? form.program_level || undefined : undefined,
            year_of_study: form.role === "student" ? form.year_of_study || undefined : undefined,
            branch: form.role === "student" ? form.branch || undefined : undefined,
            institute_unique_id: form.role === "mentor" ? form.institute_unique_id || undefined : undefined,
          })
        : api.login(form.email, form.password)
    );
    if (res) onAuthed(res);
  }

  return (
    <main className="auth">
      <div className="auth-card panel">
        <button className="link-btn" onClick={onBack}>Back to home</button>
        <h1>{registering ? "Create your account" : "Sign in to MentorConnect"}</h1>

        <div className="segmented segmented-wide" role="tablist" aria-label="Sign in or register">
          <button role="tab" aria-selected={!registering} className={!registering ? "on" : ""} onClick={() => { setMode("login"); action.setError(""); }}>Sign in</button>
          <button role="tab" aria-selected={registering} className={registering ? "on" : ""} onClick={() => { setMode("register"); action.setError(""); }}>Register</button>
        </div>

        <form onSubmit={submit} className="stack">
          {registering && (
            <>
              <fieldset className="fieldset">
                <legend>I am a</legend>
                <div className="radio-row">
                  {[["student", "Student"], ["mentor", "Professor / mentor"]].map(([v, label]) => (
                    <label key={v} className={`radio ${form.role === v ? "on" : ""}`}>
                      <input type="radio" name="role" value={v} checked={form.role === v} onChange={set("role")} />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>
              <label className="field"><span>Full name</span><input className="input" required minLength={2} autoComplete="name" value={form.full_name} onChange={set("full_name")} /></label>
              {form.role === "mentor" && (
                <label className="field"><span>Your expertise (comma separated)</span><input className="input" value={form.expertise} onChange={set("expertise")} placeholder="Machine Learning, Python" /></label>
              )}

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

              {needsUniqueId && (
                <label className="field">
                  <span>Institute-issued unique ID</span>
                  <input
                    className="input" required value={form.institute_unique_id} onChange={set("institute_unique_id")}
                    placeholder="e.g., VITCMPN111 -- helps admins verify you faster"
                  />
                </label>
              )}

              {form.role === "student" && (
                <>
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
                </>
              )}
            </>
          )}
          <label className="field"><span>Email</span><input type="email" className="input" required autoComplete="email" value={form.email} onChange={set("email")} /></label>
          <label className="field">
            <span>Password{registering && " (at least 8 characters)"}</span>
            <input type="password" className="input" required minLength={registering ? 8 : 1} autoComplete={registering ? "new-password" : "current-password"} value={form.password} onChange={set("password")} />
          </label>
          <ErrorNote>{action.error}</ErrorNote>
          <button className="btn btn-primary btn-block" disabled={action.busy}>
            {action.busy ? "Please wait…" : registering ? "Create account" : "Sign in"}
          </button>
        </form>

      </div>
    </main>
  );
}