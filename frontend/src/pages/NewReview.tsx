import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { createReview } from "../api/client";
import AgentProgress from "../components/AgentProgress";

type Step = "form" | "running" | "done";

const EXPERIENCE_LEVELS = [
  { value: "junior",    label: "Junior · 0–2 years" },
  { value: "mid",       label: "Mid-level · 2–5 years" },
  { value: "senior",    label: "Senior · 5+ years" },
  { value: "principal", label: "Principal / Staff" },
];

export default function NewReview() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("form");
  const [reviewId, setReviewId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const [form, setForm] = useState({
    repo_url: "",
    user_email: "",
    experience_level: "mid",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("repo_url", form.repo_url);
      fd.append("user_email", form.user_email);
      fd.append("experience_level", form.experience_level);
      if (fileRef.current?.files?.[0]) fd.append("requirements_pdf", fileRef.current.files[0]);
      const res = await createReview(fd);
      setReviewId(res.review_id);
      setStep("running");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start review");
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = useCallback(() => setStep("done"), []);

  if (step === "running" || step === "done") {
    return (
      <div style={{ padding: "40px", maxWidth: 680, margin: "0 auto" }}>
        <button
          onClick={() => navigate("/")}
          className="btn-ghost"
          style={{ marginBottom: 28, fontSize: "0.8rem" }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
          </svg>
          Dashboard
        </button>

        <div className="animate-fade-up" style={{ marginBottom: 24 }}>
          <div className="font-mono" style={{ fontSize: "0.7rem", color: "#6366f1", marginBottom: 6, letterSpacing: "0.06em" }}>
            REVIEW · {reviewId.slice(0, 8).toUpperCase()}
          </div>
          <h1 className="font-display" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#e8e8f0" }}>
            {step === "done" ? "Analysis Complete" : "Analysis Running"}
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#8a8aaa", marginTop: 4 }}>
            {step === "done"
              ? "All pipeline stages finished. Your report is ready."
              : "11 AI agents are analyzing your repository in real-time."}
          </p>
        </div>

        <div className="animate-fade-up delay-1">
          <AgentProgress reviewId={reviewId} onComplete={handleComplete} />
        </div>

        {step === "done" && (
          <div className="animate-fade-up delay-2" style={{ marginTop: 20 }}>
            <div className="card" style={{
              padding: "20px 24px",
              background: "rgba(34,197,94,0.06)",
              borderColor: "rgba(34,197,94,0.2)",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#22c55e", marginBottom: 2 }}>
                  Review complete
                </div>
                <div style={{ fontSize: "0.75rem", color: "#6a6a88" }}>
                  Scores, findings, and coaching are ready to view
                </div>
              </div>
              <button className="btn-primary" onClick={() => navigate(`/review/${reviewId}`)}>
                View Report
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ padding: "40px", maxWidth: 600, margin: "0 auto" }}>
      <button onClick={() => navigate("/")} className="btn-ghost" style={{ marginBottom: 28, fontSize: "0.8rem" }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
        </svg>
        Dashboard
      </button>

      <div className="animate-fade-up" style={{ marginBottom: 32 }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 12,
          fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase",
          color: "#6366f1", background: "rgba(99,102,241,0.1)",
          border: "1px solid rgba(99,102,241,0.2)", padding: "3px 10px", borderRadius: 99,
        }}>
          11 agents · 5–15 minutes
        </div>
        <h1 className="font-display" style={{ fontSize: "1.875rem", fontWeight: 800, color: "#e8e8f0", lineHeight: 1.1 }}>
          New Review
        </h1>
        <p style={{ fontSize: "0.875rem", color: "#8a8aaa", marginTop: 8, lineHeight: 1.6 }}>
          Submit any public GitHub repository for automated multi-agent analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="animate-fade-up delay-1">
        <div className="card" style={{ padding: "28px" }}>
          {/* Repo URL */}
          <div style={{ marginBottom: 20 }}>
            <label className="field-label">Repository URL <span style={{ color: "#ef4444" }}>*</span></label>
            <div style={{ position: "relative" }}>
              <div style={{
                position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)",
                color: "#4a4a68", pointerEvents: "none",
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
                </svg>
              </div>
              <input
                type="url" required
                placeholder="https://github.com/owner/repo"
                value={form.repo_url}
                onChange={(e) => setForm({ ...form, repo_url: e.target.value })}
                className="input-field font-mono"
                style={{ paddingLeft: 36, fontSize: "0.8125rem" }}
              />
            </div>
          </div>

          {/* Email */}
          <div style={{ marginBottom: 20 }}>
            <label className="field-label">Developer Email <span style={{ color: "#ef4444" }}>*</span></label>
            <input
              type="email" required
              placeholder="you@company.com"
              value={form.user_email}
              onChange={(e) => setForm({ ...form, user_email: e.target.value })}
              className="input-field"
            />
          </div>

          {/* Experience level */}
          <div style={{ marginBottom: 20 }}>
            <label className="field-label">Experience Level</label>
            <select
              value={form.experience_level}
              onChange={(e) => setForm({ ...form, experience_level: e.target.value })}
              className="input-field"
              style={{ cursor: "pointer" }}
            >
              {EXPERIENCE_LEVELS.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
            <p style={{ fontSize: "0.7rem", color: "#4a4a68", marginTop: 5 }}>
              Used to calibrate the coaching recommendations
            </p>
          </div>

          {/* PDF upload */}
          <div style={{ marginBottom: 24 }}>
            <label className="field-label">
              Requirements Document
              <span style={{ color: "#4a4a68", fontWeight: 400, textTransform: "none", letterSpacing: 0, marginLeft: 4 }}>(optional)</span>
            </label>
            <div
              style={{
                border: "1px dashed rgba(255,255,255,0.1)", borderRadius: 8,
                padding: "16px", textAlign: "center", cursor: "pointer",
                background: fileName ? "rgba(99,102,241,0.06)" : "rgba(255,255,255,0.02)",
                transition: "all 0.15s",
              }}
              onClick={() => fileRef.current?.click()}
            >
              {fileName ? (
                <div style={{ fontSize: "0.8rem", color: "#818cf8", fontFamily: "JetBrains Mono, monospace" }}>
                  {fileName}
                </div>
              ) : (
                <>
                  <div style={{ fontSize: "0.8rem", color: "#4a4a68", marginBottom: 2 }}>
                    Click to upload PDF
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#4a4a68" }}>
                    Checks requirements alignment against the codebase
                  </div>
                </>
              )}
            </div>
            <input
              type="file" accept=".pdf" ref={fileRef} style={{ display: "none" }}
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")}
            />
          </div>

          {error && (
            <div style={{
              padding: "10px 14px", borderRadius: 8, marginBottom: 16,
              background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
              fontSize: "0.8rem", color: "#f87171",
            }}>
              {error}
            </div>
          )}

          <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
            {loading ? (
              <>
                <div style={{
                  width: 13, height: 13, border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "white", borderRadius: "50%",
                }} className="animate-spin-slow" />
                Starting review…
              </>
            ) : (
              <>
                Run Analysis
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                </svg>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
