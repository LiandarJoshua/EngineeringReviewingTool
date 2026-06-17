import { useState } from "react";
import { api } from "../api/client";

interface PRReviewResult {
  pr_review_id: string;
  status: string;
  message: string;
}

interface FormState {
  repo_full_name:    string;
  pr_number:         string;
  head_sha:          string;
  pr_title:          string;
  pr_description:    string;
  author:            string;
  github_token:      string;
  experience_level:  string;
  quality_threshold: string;
}

const DEFAULT: FormState = {
  repo_full_name:    "",
  pr_number:         "",
  head_sha:          "",
  pr_title:          "",
  pr_description:    "",
  author:            "",
  github_token:      "",
  experience_level:  "mid",
  quality_threshold: "70",
};

const GUARDRAILS = [
  { icon: "🚫", text: "Never auto-merges — explicit human approval always required" },
  { icon: "🔒", text: "Never sends GitHub 'Approve' event — only comments or request changes" },
  { icon: "⚠️", text: "Critical and security issues always escalated to human reviewers" },
  { icon: "🤖", text: "AI acts as junior partner — catches syntax, style, and obvious bugs" },
  { icon: "🧠", text: "Architecture, scalability, and business logic decisions stay with humans" },
];

const STEPS = [
  { n: "01", title: "Fetch PR Diff",      desc: "Download changed files and full diff from GitHub" },
  { n: "02", title: "Run Review Agents",  desc: "Security, style, naming, bug, and performance analysis" },
  { n: "03", title: "Post Inline Comments", desc: "Suggestion blocks for 1-click fixes; warnings for human review" },
  { n: "04", title: "Quality Gate Check", desc: "Score computed from findings; threshold must be ≥ 70" },
  { n: "05", title: "Self-Correction",    desc: "Up to 3 passes until quality threshold is met" },
  { n: "06", title: "Apply Labels",       desc: "ai:reviewed · ai:needs-human-review · ai:quality-gate-failed" },
];

export default function PRReviews() {
  const [form, setForm]       = useState<FormState>(DEFAULT);
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<PRReviewResult | null>(null);
  const [error, setError]     = useState("");

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const res = await api.post("/webhooks/pr-review", {
        ...form,
        pr_number:         parseInt(form.pr_number, 10),
        quality_threshold: parseInt(form.quality_threshold, 10),
      });
      setResult(res.data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Failed to trigger PR review.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "40px", maxWidth: 900, margin: "0 auto" }}>
      <div className="animate-fade-up" style={{ marginBottom: 32 }}>
        <h1 className="font-display" style={{ fontSize: "1.75rem", fontWeight: 800, color: "#e8e8f0", marginBottom: 8 }}>
          PR Review Loop<span style={{ color: "#6366f1" }}>.</span>
        </h1>
        <p style={{ fontSize: "0.875rem", color: "#8a8aaa" }}>
          Autonomous code review on pull requests — inline comments, suggestion blocks, and quality gating.
        </p>
      </div>

      {/* Guardrails panel */}
      <div className="animate-fade-up delay-1 card" style={{ padding: "20px 24px", marginBottom: 28, borderColor: "rgba(99,102,241,0.2)" }}>
        <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6366f1", marginBottom: 12 }}>
          Active Guardrails
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {GUARDRAILS.map((g) => (
            <div key={g.text} style={{ display: "flex", gap: 10, fontSize: "0.8rem", color: "#c0c0d0", lineHeight: 1.5 }}>
              <span style={{ flexShrink: 0 }}>{g.icon}</span>
              {g.text}
            </div>
          ))}
        </div>
      </div>

      {/* PIV Loop steps */}
      <div className="animate-fade-up delay-2" style={{ marginBottom: 32 }}>
        <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 14 }}>
          PIV Loop — How It Works
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {STEPS.map((s) => (
            <div key={s.n} className="card" style={{ padding: "14px 16px", display: "flex", gap: 12, alignItems: "flex-start" }}>
              <span className="font-mono" style={{ fontSize: "0.65rem", color: "#4a4a68", flexShrink: 0, paddingTop: 2 }}>{s.n}</span>
              <div>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#e8e8f0", marginBottom: 2 }}>{s.title}</div>
                <div style={{ fontSize: "0.7rem", color: "#6a6a88", lineHeight: 1.5 }}>{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trigger form */}
      <div className="animate-fade-up delay-3 card" style={{ padding: "28px 32px" }}>
        <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 20 }}>
          Trigger PR Review Manually
        </div>

        {result && (
          <div style={{
            padding: "16px 20px", borderRadius: 10, marginBottom: 20,
            background: "rgba(34,197,94,0.07)", border: "1px solid rgba(34,197,94,0.2)",
            fontSize: "0.8rem", color: "#4ade80",
          }}>
            ✓ {result.message}
            <div className="font-mono" style={{ fontSize: "0.65rem", color: "#4a4a68", marginTop: 4 }}>
              Review ID: {result.pr_review_id}
            </div>
          </div>
        )}

        {error && (
          <div style={{
            padding: "14px 18px", borderRadius: 10, marginBottom: 20,
            background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)",
            fontSize: "0.8rem", color: "#f87171",
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div>
              <div className="field-label">Repository (owner/repo)</div>
              <input
                className="input-field"
                placeholder="octocat/hello-world"
                value={form.repo_full_name}
                onChange={set("repo_full_name")}
                required
              />
            </div>
            <div>
              <div className="field-label">PR Number</div>
              <input
                className="input-field"
                type="number"
                placeholder="42"
                value={form.pr_number}
                onChange={set("pr_number")}
                required
              />
            </div>
          </div>

          <div>
            <div className="field-label">Head SHA (latest commit on PR branch)</div>
            <input
              className="input-field font-mono"
              placeholder="a1b2c3d4e5f6..."
              value={form.head_sha}
              onChange={set("head_sha")}
              required
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div>
              <div className="field-label">PR Title (optional)</div>
              <input className="input-field" placeholder="Add OAuth2 login" value={form.pr_title} onChange={set("pr_title")} />
            </div>
            <div>
              <div className="field-label">Author (optional)</div>
              <input className="input-field" placeholder="github-username" value={form.author} onChange={set("author")} />
            </div>
          </div>

          <div>
            <div className="field-label">GitHub Personal Access Token</div>
            <input
              className="input-field font-mono"
              type="password"
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              value={form.github_token}
              onChange={set("github_token")}
              required
            />
            <div style={{ fontSize: "0.65rem", color: "#4a4a68", marginTop: 4 }}>
              Required scopes: <span className="font-mono">pull_requests:write</span> + <span className="font-mono">contents:read</span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div>
              <div className="field-label">Experience Level</div>
              <select className="input-field" value={form.experience_level} onChange={set("experience_level")}>
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="principal">Principal</option>
              </select>
            </div>
            <div>
              <div className="field-label">Quality Threshold (0–100)</div>
              <input
                className="input-field"
                type="number" min="0" max="100"
                value={form.quality_threshold}
                onChange={set("quality_threshold")}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ alignSelf: "flex-start", marginTop: 4 }}
          >
            {loading ? (
              <>
                <div style={{ width: 12, height: 12, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white", borderRadius: "50%" }} className="animate-spin-slow" />
                Queueing…
              </>
            ) : (
              <>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Trigger PR Review
              </>
            )}
          </button>
        </form>
      </div>

      {/* CI/CD setup */}
      <div className="animate-fade-up delay-3" style={{ marginTop: 28 }}>
        <div className="card" style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 12 }}>
            GitHub Actions Setup
          </div>
          <div style={{ fontSize: "0.8rem", color: "#8a8aaa", marginBottom: 14, lineHeight: 1.6 }}>
            Copy <span className="font-mono" style={{ color: "#6366f1" }}>.github/workflows/ai-review.yml</span> into your repo and add these repository secrets:
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { key: "REVIEW_API_URL", val: "http://your-api-domain:8000 (public URL of this API)" },
            ].map(({ key, val }) => (
              <div key={key} style={{ display: "flex", gap: 12, padding: "8px 12px", borderRadius: 7, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <span className="font-mono" style={{ fontSize: "0.75rem", color: "#6366f1", flexShrink: 0 }}>{key}</span>
                <span style={{ fontSize: "0.75rem", color: "#6a6a88" }}>{val}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, fontSize: "0.75rem", color: "#4a4a68", lineHeight: 1.6 }}>
            The workflow fires automatically on every PR open/update. GITHUB_TOKEN is provided by Actions automatically.
            <br />
            For local dev, expose the API with <span className="font-mono" style={{ color: "#6366f1" }}>ngrok http 8000</span> and use the tunnel URL as REVIEW_API_URL.
          </div>
        </div>
      </div>
    </div>
  );
}
