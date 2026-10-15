import { useEffect, useState } from "react";
import { api } from "../api";
import { ErrorNote, useAction } from "./ui";

const STATUS = [
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
];

export default function RoadmapPanel() {
  const [goal, setGoal] = useState("");
  const [roadmaps, setRoadmaps] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const gen = useAction();
  const list = useAction();

  useEffect(() => {
    list.run(async () => {
      const rows = await api.roadmaps();
      setRoadmaps(rows);
      setActiveId(rows[0]?.id ?? null);
      setLoaded(true);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const active = roadmaps.find((r) => r.id === activeId);

  async function generate(text, replaceId) {
    const clean = text.trim();
    if (clean.length < 2) return gen.setError("Enter a role or skill you want to work toward, such as Senior AI Agent Developer.");
    const created = await gen.run(() => api.generateRoadmap(clean, replaceId));
    if (created) {
      setRoadmaps((prev) => [created, ...prev.filter((r) => r.id !== replaceId)]);
      setActiveId(created.id);
      if (!replaceId) setGoal("");
    }
  }

  async function setStatus(milestone, status) {
    if (milestone.status === status) return;
    const before = roadmaps;
    const patch = (rows) =>
      rows.map((r) => {
        if (r.id !== activeId) return r;
        const milestones = r.milestones.map((m) => (m.id === milestone.id ? { ...m, status } : m));
        const done = milestones.filter((m) => m.status === "completed").length;
        return { ...r, milestones, progress: Math.round((100 * done) / milestones.length) };
      });
    setRoadmaps(patch(roadmaps)); // optimistic
    try {
      await api.updateMilestone(milestone.id, status);
    } catch (e) {
      setRoadmaps(before);
      gen.setError(e.message);
    }
  }

  async function remove(id) {
    if (!window.confirm("Delete this roadmap?")) return;
    const ok = await gen.run(async () => {
      await api.deleteRoadmap(id);
      return true;
    });
    if (ok) {
      const rest = roadmaps.filter((r) => r.id !== id);
      setRoadmaps(rest);
      setActiveId(rest[0]?.id ?? null);
    }
  }

  return (
    <section className="panel" id="roadmaps" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title" className="panel-title">Dynamic AI career roadmaps</h2>
      <p className="panel-sub">Enter the role you're aiming for. Gemini plans your four engineering milestones.</p>

      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          generate(goal);
        }}
      >
        <label className="sr-only" htmlFor="goal">Target role</label>
        <input
          id="goal"
          className="input grow"
          value={goal}
          maxLength={120}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g., Senior Systems Architect"
        />
        <button className="btn btn-primary" disabled={gen.busy}>
          {gen.busy ? "Planning…" : "Generate roadmap"}
        </button>
      </form>
      <ErrorNote>{gen.error || list.error}</ErrorNote>

      {roadmaps.length > 1 && (
        <div className="chips" role="tablist" aria-label="Your roadmaps">
          {roadmaps.map((r) => (
            <button
              key={r.id}
              role="tab"
              aria-selected={r.id === activeId}
              className={`chip chip-btn ${r.id === activeId ? "chip-on" : ""}`}
              onClick={() => setActiveId(r.id)}
            >
              {r.goal}
            </button>
          ))}
        </div>
      )}

      {!active && loaded && !gen.busy && (
        <p className="empty">No roadmap yet. Enter a target role above and generate your first one.</p>
      )}
      {gen.busy && !active && <p className="empty" aria-live="polite">Gemini is planning your milestones…</p>}

      {active && (
        <div className="roadmap">
          <div className="roadmap-head">
            <h3 className="roadmap-goal">Target: {active.goal}</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => remove(active.id)}>Delete</button>
          </div>

          <div className="progress" role="progressbar" aria-valuenow={active.progress} aria-valuemin={0} aria-valuemax={100} aria-label="Roadmap progress">
            <span style={{ width: `${active.progress}%` }} />
          </div>
          <p className="muted small">{active.progress}% complete</p>

          {active.error_message && (
            <div className="banner banner-warn" role="alert">
              <p>
                <strong>Gemini couldn't build this roadmap.</strong> Showing a general template instead.
              </p>
              <p className="banner-detail">{active.error_message}</p>
              <button className="btn btn-sm" disabled={gen.busy} onClick={() => generate(active.goal, active.id)}>
                {gen.busy ? "Retrying…" : "Retry with Gemini"}
              </button>
            </div>
          )}

          <ol className="track">
            {active.milestones.map((m) => (
              <li key={m.id} className={`stop stop-${m.status}`}>
                <span className="stop-node" aria-hidden="true">{m.status === "completed" ? "✓" : m.position}</span>
                <div className="stop-body">
                  <div className="stop-meta">
                    <span>Milestone {m.position}</span>
                    {m.duration_weeks && <span>{m.duration_weeks} weeks</span>}
                  </div>
                  <h4>{m.title}</h4>
                  <p>{m.description}</p>
                  {m.topics.length > 0 && (
                    <ul className="chips chips-tight">
                      {m.topics.map((t) => (
                        <li key={t} className="chip">{t}</li>
                      ))}
                    </ul>
                  )}
                  <div className="segmented" role="group" aria-label={`Status of milestone ${m.position}`}>
                    {STATUS.map((s) => (
                      <button
                        key={s.value}
                        className={m.status === s.value ? "on" : ""}
                        aria-pressed={m.status === s.value}
                        onClick={() => setStatus(m, s.value)}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
