import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("erp_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to /login on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.includes("/login")) {
      localStorage.removeItem("erp_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = async (email: string, password: string): Promise<string> => {
  const form = new URLSearchParams({ username: email, password });
  const res  = await axios.post(`${BASE_URL}/auth/login`, form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  const token: string = res.data.access_token;
  localStorage.setItem("erp_token", token);
  return token;
};

export const logout = () => {
  localStorage.removeItem("erp_token");
  window.location.href = "/login";
};

export const isAuthenticated = () => !!localStorage.getItem("erp_token");

export interface ReviewCreateResponse {
  review_id: string;
  job_id: string;
  status: string;
}

export interface ReviewResponse {
  id: string;
  status: string;
  overall_score: number | null;
  security_score: number | null;
  architecture_score: number | null;
  testing_score: number | null;
  scalability_score: number | null;
  debt_score: number | null;
  coaching_report?: object | null;
}

export interface Finding {
  id: string;
  agent_name: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  issue: string;
  recommendation: string;
  file_path: string;
  line_number: number | null;
}

export interface ProgressEntry {
  review_number: number;
  security: number;
  architecture: number;
  testing: number;
  scalability: number;
  overall: number;
}

export interface ReviewListItem {
  id: string;
  status: string;
  overall_score: number | null;
  security_score: number | null;
  architecture_score: number | null;
  testing_score: number | null;
  scalability_score: number | null;
  debt_score: number | null;
  repo_url: string;
  repo_name: string;
  user_email: string;
  created_at: string | null;
}

export const listReviews = async (limit = 20): Promise<ReviewListItem[]> => {
  const res = await api.get(`/reviews/?limit=${limit}`);
  return res.data;
};

export const createReview = async (formData: FormData): Promise<ReviewCreateResponse> => {
  const res = await api.post("/reviews/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const getReview = async (reviewId: string): Promise<ReviewResponse> => {
  const res = await api.get(`/reviews/${reviewId}`);
  return res.data;
};

export const getFindings = async (
  reviewId: string,
  severity?: string,
  page = 1
): Promise<Finding[]> => {
  const params: Record<string, unknown> = { page, size: 50 };
  if (severity) params.severity = severity;
  const res = await api.get(`/reviews/${reviewId}/findings`, { params });
  return res.data;
};

export const cancelReview = async (reviewId: string): Promise<void> => {
  await api.post(`/reviews/${reviewId}/cancel`);
};

export const deleteReview = async (reviewId: string): Promise<void> => {
  await api.delete(`/reviews/${reviewId}`);
};

export const generateCoaching = async (reviewId: string, experienceLevel = "mid"): Promise<{ job_id: string }> => {
  const res = await api.post(`/reviews/${reviewId}/coaching?experience_level=${experienceLevel}`);
  return res.data;
};

export const getProgress = async (
  userId: string,
  repoId: string
): Promise<{ history: ProgressEntry[] }> => {
  const res = await api.get(`/reviews/users/${userId}/progress`, {
    params: { repo_id: repoId },
  });
  return res.data;
};

// ── Feedback ─────────────────────────────────────────────────────────────────

export type FeedbackAction = "dismissed" | "confirmed" | "fixed";

export interface FeedbackResponse {
  finding_id: string;
  action: FeedbackAction;
  reason: string;
}

export const submitFeedback = async (
  findingId: string,
  action: FeedbackAction,
  reason = ""
): Promise<FeedbackResponse> => {
  const res = await api.post(`/findings/${findingId}/feedback`, { action, reason });
  return res.data;
};

export const getFeedback = async (findingId: string): Promise<FeedbackResponse | null> => {
  const res = await api.get(`/findings/${findingId}/feedback`);
  return res.data;
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardStats {
  totals: { reviews: number; complete_reviews: number; findings: number; repos: number };
  averages: { overall: number | null; security: number | null; architecture: number | null; testing: number | null; scalability: number | null; debt: number | null };
  by_severity: Record<string, number>;
  by_category: { category: string; count: number }[];
  feedback_summary: Record<string, number>;
  grade_distribution: Record<string, number>;
  top_repos: { repo_name: string; repo_url: string; overall_score: number | null; security_score: number | null; last_reviewed: string | null }[];
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const res = await api.get("/dashboard/stats");
  return res.data;
};

// ── Schedules ─────────────────────────────────────────────────────────────────

export interface Schedule {
  id: string;
  repo_url: string;
  repo_name: string;
  user_email: string;
  interval_hours: number;
  interval_label: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export const listSchedules = async (): Promise<Schedule[]> => {
  const res = await api.get("/schedules/");
  return res.data;
};

export const createSchedule = async (
  repo_url: string,
  user_email: string,
  interval: "daily" | "weekly" | "monthly"
): Promise<Schedule> => {
  const res = await api.post("/schedules/", { repo_url, user_email, interval });
  return res.data;
};

export const toggleSchedule = async (id: string): Promise<Schedule> => {
  const res = await api.patch(`/schedules/${id}/toggle`);
  return res.data;
};

export const deleteSchedule = async (id: string): Promise<void> => {
  await api.delete(`/schedules/${id}`);
};
