import { useLocation } from "react-router-dom";

const VIDEO_SRC = "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260314_131748_f2ca2a28-fed7-44c8-b9a9-bd9acdd5ec31.mp4";

/** Mounted once at the app root (outside all routes) so the video never reloads or restarts
 * on navigation -- only the blur/dim treatment changes based on which page is showing. */
export default function VideoBackground() {
  const { pathname } = useLocation();
  const isHome = pathname === "/";

  return (
    <div className={`app-video-wrap ${isHome ? "app-video-clear" : "app-video-blurred"}`} aria-hidden="true">
      <video className="app-video" autoPlay loop muted playsInline>
        <source src={VIDEO_SRC} type="video/mp4" />
      </video>
      <div className="app-video-scrim" />
    </div>
  );
}