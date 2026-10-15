import { NavLink, useLocation, useNavigate } from "react-router-dom";
import NotificationBell from "./NotificationBell";

// Guest links scroll to anchor sections on the single public page ("/") -- they are NOT
// separate routes. Works from any page: if not already on "/", navigate there first, then
// scroll once the page has rendered.
const GUEST_LINKS = [
  ["Home", "home"],
  ["Our Vision", "vision"],
  ["Reach Us", "reach-us"],
];
const STUDENT_LINKS = [
  ["Mentors", "/app/mentors"],
  ["Roadmaps", "/app/roadmaps"],
  ["Sessions", "/app/sessions"],
  ["Profile", "/app/profile"],
];
const MENTOR_LINKS = [
  ["Sessions", "/app/sessions"],
  ["Availability", "/app/availability"],
  ["Verification", "/app/verification"],
  ["Profile", "/app/profile"],
];
const ADMIN_LINKS = [["Verifications", "/app"]];

function GuestNavLinks() {
  const navigate = useNavigate();
  const location = useLocation();

  function goTo(id) {
    if (location.pathname !== "/") {
      navigate(`/#${id}`);
      requestAnimationFrame(() => {
        setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }), 50);
      });
    } else {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    }
  }

  return (
    <ul>
      {GUEST_LINKS.map(([label, id]) => (
        <li key={id}>
          <a href={`/#${id}`} onClick={(e) => { e.preventDefault(); goTo(id); }}>{label}</a>
        </li>
      ))}
    </ul>
  );
}

export default function Navbar({ user, onSignOut }) {
  const navigate = useNavigate();
  const links = user?.role === "mentor" ? MENTOR_LINKS : user?.role === "admin" ? ADMIN_LINKS : user ? STUDENT_LINKS : null;
  const homeHref = user ? links[0][1] : "/";

  return (
    <header className="nav">
      <NavLink className="wordmark" to={homeHref} end={!user}>
        MentorConnect<sup>®</sup>
      </NavLink>
      <nav aria-label="Main">
        {user ? (
          <ul>
            {links.map(([label, to]) => (
              <li key={to}>
                <NavLink to={to} end className={({ isActive }) => (isActive ? "nav-active" : undefined)}>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        ) : (
          <GuestNavLinks />
        )}
      </nav>
      {user ? (
        <div className="nav-user">
          {(user.role === "student" || user.role === "mentor") && <NotificationBell />}
          <span className="muted small">{user.full_name}</span>
          <button className="btn btn-outline btn-sm" onClick={onSignOut}>Sign out session</button>
        </div>
      ) : (
        <button className="btn btn-outline btn-sm" onClick={() => navigate("/login")}>Sign in</button>
      )}
    </header>
  );
}