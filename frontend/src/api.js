// Thin wrapper around fetch for the MentorConnect API.
const BASE = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const TOKEN_KEY = "mentorconnect_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => (onUnauthorized = fn);

function formatDetail(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = (d.loc || []).filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return `Request failed (HTTP ${status}).`;
}

async function request(path, { method = "GET", body, params, form } = {}) {
  const url = new URL(BASE + path);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== 0) url.searchParams.set(k, v);
  });

  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  // form (FormData) sets its own multipart Content-Type with boundary -- don't set it manually
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: form !== undefined ? form : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      `Can't reach the MentorConnect server at ${BASE}. Start the backend (uvicorn main:app --reload) and try again.`,
      0
    );
  }

  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body */
  }

  if (!res.ok) {
    if (res.status === 401 && token && !path.startsWith("/auth/login")) onUnauthorized();
    throw new ApiError(formatDetail(data?.detail, res.status), res.status);
  }
  return data;
}

/** Downloads a protected file (needs the auth header) and opens/saves it via a blob URL. */
async function downloadFile(path, suggestedName) {
  const token = getToken();
  const res = await fetch(BASE + path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status}).`;
    try {
      detail = formatDetail((await res.json())?.detail, res.status);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = suggestedName || "document";
  a.target = "_blank";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export const api = {
  baseUrl: BASE,
  health: () => request("/health"),
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),
  register: (payload) => request("/auth/register", { method: "POST", body: payload }),
  me: () => request("/auth/me"),

  mentors: (params) => request("/mentors/", { params }),
  mentor: (mentorId) => request(`/mentors/${mentorId}`),
  mentorBusy: (mentorId) => request(`/mentors/${mentorId}/busy`),
  mentorReviews: (mentorId) => request(`/mentors/${mentorId}/reviews`),
  skills: () => request("/mentors/skills"),
  myMentorProfile: () => request("/mentors/me"),
  updateMentorProfile: (body) => request("/mentors/me", { method: "PUT", body }),
  myStudentProfile: () => request("/students/me"),
  updateStudentProfile: (body) => request("/students/me", { method: "PUT", body }),

  roadmaps: () => request("/roadmaps/"),
  generateRoadmap: (goal, replaceId) =>
    request("/roadmaps/generate", { method: "POST", body: { goal, replace_id: replaceId ?? null } }),
  updateMilestone: (id, status) => request(`/roadmaps/milestones/${id}`, { method: "PATCH", body: { status } }),
  deleteRoadmap: (id) => request(`/roadmaps/${id}`, { method: "DELETE" }),

  bookings: () => request("/bookings/me"),
  createBooking: (body) => request("/bookings/", { method: "POST", body }),
  setBookingStatus: (id, status, reason) => request(`/bookings/${id}/status`, { method: "PATCH", body: { status, reason } }),
  rescheduleBooking: (id, scheduledAt, reason) =>
    request(`/bookings/${id}/reschedule`, { method: "PATCH", body: { scheduled_at: scheduledAt, reason } }),
  reviewBooking: (id, rating, feedback) =>
    request(`/bookings/${id}/review`, { method: "POST", body: { rating, feedback } }),
  updateBookingLocation: (id, location) => request(`/bookings/${id}/location`, { method: "PATCH", body: { location } }),

  // AI session notes + "remembers this student"
  addSessionNotes: (bookingId, feedback) => request(`/bookings/${bookingId}/notes`, { method: "POST", body: { feedback } }),
  sessionNotes: (bookingId) => request(`/bookings/${bookingId}/notes`),
  studentMemory: (studentId) => request(`/mentors/students/${studentId}/memory`),

  // Weekly availability slots (SRS REQ-5-1)
  mySlots: () => request("/mentors/me/slots"),
  replaceMySlots: (slots) => request("/mentors/me/slots", { method: "PUT", body: { slots } }),

  // In-app notifications
  notifications: () => request("/notifications/me"),
  unreadCount: () => request("/notifications/me/unread-count"),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () => request("/notifications/read-all", { method: "POST" }),
  // Mentor verification (SRS 4.2)
  myVerification: () => request("/mentors/me/verification"),
  submitVerification: (path, file) => {
    const form = new FormData();
    form.append("path", path);
    form.append("document", file);
    return request("/mentors/me/verification", { method: "POST", form });
  },

  // Admin review queue
  adminVerifications: (statusFilter) => request("/admin/verifications", { params: { status_filter: statusFilter } }),
  adminApprove: (mentorId) => request(`/admin/verifications/${mentorId}/approve`, { method: "POST" }),
  adminReject: (mentorId, reason) => request(`/admin/verifications/${mentorId}/reject`, { method: "POST", body: { reason } }),
  adminDownloadDocument: (mentorId, filename) => downloadFile(`/admin/verifications/${mentorId}/document`, filename),
};