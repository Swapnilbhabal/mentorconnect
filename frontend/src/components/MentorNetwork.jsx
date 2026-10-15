import { useEffect, useState } from "react";
import { api } from "../api";
import BookingDialog from "./BookingDialog";
import { Link } from "react-router-dom";
import { Avatar, ErrorNote, MODE_LABELS, RatingBadge, slotsToLocalSummary, VerifiedBadge } from "./ui";

export default function MentorNetwork({ onBooked }) {
  const [filters, setFilters] = useState({ q: "", expertise: "", mode: "", min_rating: 0, sort: "rating" });
  const [mentors, setMentors] = useState(null);
  const [skills, setSkills] = useState([]);
  const [error, setError] = useState("");
  const [booking, setBooking] = useState(null);

  const set = (key) => (e) => setFilters((f) => ({ ...f, [key]: key === "min_rating" ? Number(e.target.value) : e.target.value }));

  useEffect(() => {
    api.skills().then(setSkills).catch(() => {});
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .mentors(filters)
        .then((rows) => {
          setMentors(rows);
          setError("");
        })
        .catch((e) => setError(e.message));
    }, 250); // debounce typing
    return () => clearTimeout(timer);
  }, [filters]);

  const filtered = Boolean(filters.q || filters.expertise || filters.mode || filters.min_rating);

  return (
    <section className="panel" id="mentors" aria-labelledby="mentor-title">
      <h2 id="mentor-title" className="panel-title">Verified mentor network</h2>
      <p className="panel-sub">Filter by skill, meeting type or rating, then book a one-to-one session.</p>

      <div className="filters">
        <label className="sr-only" htmlFor="mentor-search">Search mentors</label>
        <input id="mentor-search" className="input grow" placeholder="Search by expertise (e.g., React) or name…" value={filters.q} onChange={set("q")} />
        <select className="input" aria-label="Skill" value={filters.expertise} onChange={set("expertise")}>
          <option value="">Any skill</option>
          {skills.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="input" aria-label="Meeting type" value={filters.mode} onChange={set("mode")}>
          <option value="">Any meeting type</option>
          {Object.entries(MODE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="input" aria-label="Minimum rating" value={filters.min_rating} onChange={set("min_rating")}>
          <option value={0}>Any rating</option>
          <option value={4}>4+ stars</option>
          <option value={4.5}>4.5+ stars</option>
        </select>
        <select className="input" aria-label="Sort by" value={filters.sort} onChange={set("sort")}>
          <option value="rating">Top rated first</option>
          <option value="experience">Most experienced</option>
          <option value="name">Name A–Z</option>
        </select>
      </div>

      <ErrorNote>{error}</ErrorNote>
      {mentors === null && !error && <p className="empty">Loading mentors…</p>}
      {mentors?.length === 0 && (
        <p className="empty">
          {filtered ? "No mentors match these filters. Clear a filter to see more." : "No mentors have registered yet."}
        </p>
      )}

      <ul className="mentor-list" tabIndex={0} aria-label="Mentor results">
        {mentors?.map((m) => (
          <li key={m.id} className="mentor">
            <Avatar name={m.name} src={m.avatar_url} size={56} />
            <div className="mentor-main">
              <div className="mentor-top">
                <div>
                  <h3><Link to={`${m.id}`} className="mentor-name-link">{m.name}</Link></h3>
                  <div className="row" style={{ gap: "0.4rem", marginTop: "0.15rem" }}>
                    <p className="muted small" style={{ margin: 0 }}>
                      {[m.department, m.years_experience ? `${m.years_experience} yrs experience` : null].filter(Boolean).join(", ")}
                    </p>
                    <VerifiedBadge verified={m.platform_verified} />
                  </div>
                </div>
                <RatingBadge rating={m.rating_avg} count={m.rating_count} />
              </div>
              <p className="mentor-bio">{m.bio}</p>
              <ul className="chips chips-tight">
                {m.expertise_list.map((s) => <li key={s} className="chip">{s}</li>)}
              </ul>
              <p className="muted small mentor-stats">
                {m.rating_avg ? `${m.rating_avg.toFixed(1)} rating from ${m.rating_count} reviews. ` : "No reviews yet. "}
                {m.sessions_completed > 0 && `${m.sessions_completed} sessions completed. `}
                {m.slots && m.slots.length > 0
                  ? `Available (your time zone): ${slotsToLocalSummary(m.slots)}.`
                  : m.availability && `Usually available ${m.availability} (not enforced).`}
              </p>
              <div className="mentor-actions">
                <span className="muted small">
                  {m.available_modes.length ? m.available_modes.map((x) => MODE_LABELS[x]).join(" / ") : "Not accepting bookings yet"}
                </span>
                <button className="btn btn-primary btn-sm" disabled={!m.available_modes.length} onClick={() => setBooking(m)}>
                  Book session
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {booking && <BookingDialog mentor={booking} onClose={() => setBooking(null)} onBooked={onBooked} />}
    </section>
  );
}
