import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api";
import AdminHub from "./components/AdminHub";
import AuthPage from "./components/AuthPage";
import HomePage from "./components/MarketingPages";
import MentorDetailPage from "./components/MentorDetailPage";
import MentorLayout, { AvailabilityPage, MentorProfilePage, MentorSessionsPage, VerificationPage } from "./components/MentorHub";
import Navbar from "./components/Navbar";
import StudentLayout, { MentorsPage, RoadmapsPage, SessionsPage, StudentProfilePage } from "./components/StudentHub";
import VideoBackground from "./components/VideoBackground";

function RequireAuth({ user, children }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RedirectIfAuthed({ user, children }) {
  if (user) return <Navigate to="/app" replace />;
  return children;
}

// The public site is one scrollable page with anchor sections (#home/#vision/#reach-us) --
// this scrolls to the right one whenever the URL hash changes (including on first load if
// someone opens a direct link like "/#vision").
function ScrollToHash() {
  const location = useLocation();
  useEffect(() => {
    if (location.hash) {
      const id = location.hash.slice(1);
      requestAnimationFrame(() => {
        setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }), 50);
      });
    } else if (location.pathname === "/") {
      window.scrollTo({ top: 0 });
    }
  }, [location.pathname, location.hash]);
  return null;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(getToken()));
  const navigate = useNavigate();

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
    navigate("/");
  }, [navigate]);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
  }, [signOut]);

  useEffect(() => {
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setBooting(false));
  }, []);

  const onAuthed = ({ access_token, user }) => {
    setToken(access_token);
    setUser(user);
    navigate("/app");
  };

  if (booting) return <p className="boot" role="status">Loading…</p>;

  const roleElement =
    user?.role === "mentor" ? <MentorLayout user={user} /> :
    user?.role === "admin" ? <AdminHub user={user} /> :
    user ? <StudentLayout user={user} /> : null;

  return (
    <>
      <VideoBackground />
      <Navbar user={user} onSignOut={signOut} />
      <ScrollToHash />
      <Routes>
        <Route path="/" element={<RedirectIfAuthed user={user}><HomePage /></RedirectIfAuthed>} />
        <Route path="/vision" element={<Navigate to="/#vision" replace />} />
        <Route path="/reach-us" element={<Navigate to="/#reach-us" replace />} />
        <Route
          path="/login"
          element={<RedirectIfAuthed user={user}><AuthPage key="login" initialMode="login" onAuthed={onAuthed} onBack={() => navigate("/")} /></RedirectIfAuthed>}
        />
        <Route
          path="/register"
          element={<RedirectIfAuthed user={user}><AuthPage key="register" initialMode="register" onAuthed={onAuthed} onBack={() => navigate("/")} /></RedirectIfAuthed>}
        />

        <Route path="/app" element={<RequireAuth user={user}>{roleElement}</RequireAuth>}>
          {user?.role === "student" && (
            <>
              <Route index element={<Navigate to="mentors" replace />} />
              <Route path="roadmaps" element={<RoadmapsPage />} />
              <Route path="mentors" element={<MentorsPage />} />
              <Route path="mentors/:id" element={<MentorDetailPage />} />
              <Route path="sessions" element={<SessionsPage />} />
              <Route path="profile" element={<StudentProfilePage />} />
            </>
          )}
          {user?.role === "mentor" && (
            <>
              <Route index element={<Navigate to="sessions" replace />} />
              <Route path="sessions" element={<MentorSessionsPage />} />
              <Route path="availability" element={<AvailabilityPage />} />
              <Route path="verification" element={<VerificationPage />} />
              <Route path="profile" element={<MentorProfilePage />} />
            </>
          )}
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}