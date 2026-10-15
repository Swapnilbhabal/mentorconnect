import { useNavigate } from "react-router-dom";

const SAMPLE = [
  { title: "Foundations of agent design", meta: "3 weeks", state: "completed" },
  { title: "Tool use, memory and evaluation", meta: "5 weeks", state: "in_progress" },
  { title: "Ship a production agent", meta: "6 weeks", state: "pending" },
  { title: "Mock interviews and portfolio review", meta: "2 weeks", state: "pending" },
];

/** The whole public site is ONE scrollable page (Home / Our Vision / Reach Us are anchor
 * sections, not separate routes) -- Navbar scrolls to these ids instead of navigating. */
export default function HomePage() {
  const navigate = useNavigate();
  return (
    <main className="cinematic-page">
      <section className="cinematic-hero" id="home">
        <h1 className="animate-fade-rise">
          AI career roadmaps. <br />Real mentors. One place.
        </h1>
        <p className="animate-fade-rise-delay">
          Tell MentorConnect the role you're aiming for. It builds a four-milestone learning plan, then
          matches you with verified professors you can book by video call, Teams or on campus.
        </p>
        <button className="liquid-glass liquid-glass-btn cinematic-cta-hero animate-fade-rise-delay-2" onClick={() => navigate("/register")}>
          Get started free
        </button>
      </section>

      <section className="section" id="engine">
        <h2>The mentorship engine</h2>
        <div className="flow">
          <article>
            <h3>A roadmap made for your goal</h3>
            <p>Gemini turns any career target into foundations, core tooling, a capstone project and interview prep. Mark milestones as you finish them.</p>
          </article>
          <article>
            <h3>Mentors ranked by real reviews</h3>
            <p>Every professor shows a plain average rating from students who've actually had a session. Filter by skill, meeting type and rating.</p>
          </article>
          <article>
            <h3>Booked in a minute</h3>
            <p>Choose Zoom, Teams or an on-campus slot. You get the professor's own room or location, and both of you see the session.</p>
          </article>
        </div>
      </section>

      <section className="section roadmap-showcase" aria-label="Sample roadmap">
        <div className="roadmap-showcase-copy">
          <p className="eyebrow">See it in action</p>
          <h2>One goal in, a real plan out</h2>
          <p>
            Type a target role like "Senior AI Agent Developer" and Gemini builds a sequenced,
            four-milestone roadmap in seconds -- foundations first, a shippable project by the end.
            Track progress as you go, and every milestone links back to mentors who can review your work.
          </p>
        </div>
        <div className="panel hero-sample">
          <p className="muted small">Sample roadmap for "Senior AI Agent Developer"</p>
          <ol className="track">
            {SAMPLE.map((s, i) => (
              <li key={s.title} className={`stop stop-${s.state}`}>
                <span className="stop-node" aria-hidden="true">{s.state === "completed" ? "✓" : i + 1}</span>
                <div className="stop-body">
                  <h4>{s.title}</h4>
                  <p className="muted small">{s.meta}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section section-split" id="vision">
        <h2>Our vision</h2>
        <div>
          <p>
            Most students know their goal but not the path, and the best guidance sits one office away. MentorConnect
            closes that gap: an AI plan to start from, and a human who has done it to check your work.
          </p>
          <p>Mentors are rated by the students they teach, so the network gets better the more it is used.</p>
        </div>
      </section>

      <section className="section section-split" id="reach-us">
        <h2>Reach us</h2>
        <div>
          <p>
            Questions, or want your department onboarded as a mentor group? Write to{" "}
            <a href="mailto:hello@mentorconnect.example">hello@mentorconnect.example</a>.
          </p>
          <p className="muted small">Replace this address with your own before you go live.</p>
        </div>
      </section>

      <footer className="footer muted small">MentorConnect®, built with FastAPI, React and Gemini.</footer>
    </main>
  );
}