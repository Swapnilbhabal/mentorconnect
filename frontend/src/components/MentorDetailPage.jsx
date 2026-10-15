import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import BookingDialog from "./BookingDialog";
import { Avatar, ErrorNote, formatWhen, MODE_LABELS, RatingBadge, slotToLocalLabel, VerifiedBadge } from "./ui";

function ReviewsSection({ mentorId }) {
  const [reviews, setReviews] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.mentorReviews(mentorId).then(setReviews).catch((e) => setError(e.message));
  }, [mentorId]);

  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (reviews === null) return <p className="muted small">Loading reviews…</p>;
  if (reviews.length === 0) return <p className="empty">No reviews yet -- be the first to book and leave one.</p>;

  return (
    <ul className="review-list">
      {reviews.map((r, i) => (
        <li key={i} className="review-item">
          <div className="review-stars" aria-label={`${r.rating} out of 5 stars`}>
            {"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}
          </div>
          {r.feedback && <p className="review-text">{r.feedback}</p>}
          <p className="muted small">{formatWhen(r.session_date)}</p>
        </li>
      ))}
    </ul>
  );
}

export default function MentorDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [mentor, setMentor] = useState(null);
  const [error, setError] = useState("");
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    api.mentor(id).then(setMentor).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <main className="hub"><ErrorNote>{error}</ErrorNote></main>;
  if (!mentor) return null;

  return (
    <main className="hub mentor-detail">
      <button className="link-btn" onClick={() => navigate(-1)}>&larr; Back to mentors</button>

      <header className="panel mentor-detail-head">
        <Avatar name={mentor.name} src={mentor.avatar_url} size={88} />
        <div className="mentor-detail-head-info">
          <div className="row" style={{ gap: "0.6rem", flexWrap: "wrap" }}>
            <h1>{mentor.name}</h1>
            <VerifiedBadge verified={mentor.platform_verified} />
          </div>
          <p className="muted">{mentor.department}{mentor.years_experience ? ` \u00b7 ${mentor.years_experience} yrs experience` : ""}</p>
          {mentor.institute_name && (
            <p className="muted small">{mentor.institute_type_label ? `${mentor.institute_type_label} \u00b7 ` : ""}{mentor.institute_name}</p>
          )}
        </div>
        <div className="mentor-detail-head-cta">
          <RatingBadge rating={mentor.rating_avg} count={mentor.rating_count} />
          <button className="btn btn-primary" onClick={() => setBooking(true)}>Book session</button>
        </div>
      </header>

      <section className="stats panel" aria-label="Mentor statistics">
        <div className="stat"><span className="stat-value">{mentor.rating_avg ? mentor.rating_avg.toFixed(1) : "New"}</span><span className="stat-label">Rating</span></div>
        <div className="stat"><span className="stat-value">{mentor.rating_count}</span><span className="stat-label">Reviews</span></div>
        <div className="stat"><span className="stat-value">{mentor.sessions_completed}</span><span className="stat-label">Sessions completed</span></div>
        <div className="stat"><span className="stat-value">{mentor.completion_rate != null ? `${Math.round(mentor.completion_rate * 100)}%` : "\u2014"}</span><span className="stat-label">Completion rate</span></div>
      </section>

      <section className="panel">
        <h2 className="panel-title">About</h2>
        <p>{mentor.long_bio || mentor.bio || "No bio added yet."}</p>
        <h3 style={{ marginTop: "1rem" }}>Expertise</h3>
        <ul className="chips">
          {mentor.expertise_list.map((s) => <li key={s} className="chip">{s}</li>)}
        </ul>
      </section>

      <section className="panel">
        <h2 className="panel-title">Meeting options</h2>
        <ul className="chips chips-tight" style={{ marginBottom: "0.8rem" }}>
          {mentor.available_modes.map((m) => <li key={m} className="chip">{MODE_LABELS[m]}</li>)}
        </ul>
        {mentor.campus_location && <p className="small">Usual on-campus room: {mentor.campus_location}</p>}
        {mentor.slots && mentor.slots.length > 0 ? (
          <p className="small">Available (your time zone): {mentor.slots.map((s) => slotToLocalLabel(s)).join(", ")}</p>
        ) : mentor.availability ? (
          <p className="small muted">Usually available {mentor.availability} (mentor's own words, not enforced)</p>
        ) : (
          <p className="small muted">No fixed weekly hours set -- open to requests at any time.</p>
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">Reviews</h2>
        <ReviewsSection mentorId={id} />
      </section>

      {booking && <BookingDialog mentor={mentor} onClose={() => setBooking(false)} onBooked={() => {}} />}
    </main>
  );
}