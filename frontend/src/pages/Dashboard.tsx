import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listReviews, deleteReview, getDashboardStats, type ReviewListItem, type DashboardStats } from "../api/client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const FEATURES = [
  { icon: "⬡", color: "#6366f1", bg: "rgba(99,102,241,0.08)",  title: "Architecture",    desc: "Boundary violations, coupling, pattern detection" },
  { icon: "⬢", color: "#ef4444", bg: "rgba(239,68,68,0.08)",   title: "Security",        desc: "OWASP Top 10, Semgrep, Bandit, logic flaws" },
  { icon: "⬡", color: "#f59e0b", bg: "rgba(245,158,11,0.08)",  title: "Scalability",     desc: "N+1 queries, missing indexes, blocking calls" },
  { icon: "⬢", color: "#22c55e", bg: "rgba(34,197,94,0.08)",   title: "Testing",         desc: "Coverage gaps, test pyramid, edge cases" },
  { icon: "⬡", color: "#8b5cf6", bg: "rgba(139,92,246,0.08)",  title: "Technical Debt",  desc: "Complexity, dead code, god modules, TODOs" },
  { icon: "⬢", color: "#06b6d4", bg: "rgba(6,182,212,0.08)",   title: "Coaching",        desc: "Personalized roadmap by experience level" },
];

function scoreColor(v: number | null) {
  if (v === null) return "#4a4a68";
  if (v >= 80) return "#22c55e";
  if (v >= 65) return "#f59e0b";
  if (v >= 50) return "#f97316";
  return "#ef4444";
}

function scoreGrade(v: number | null) {
  if (v === null) return "—";
  if (v >= 80) return "A";
  if (v >= 65) return "B";
  if (v >= 50) return "C";
  return "D";
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);
  if (mins  < 1)  return "just now";
  if (mins  < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    complete: "#22c55e", failed: "#ef4444", running: "#6366f1", pending: "#f59e0b",
  };
  return (
    <div style={{
      width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
      background: colors[status] ?? "#4a4a68",
      boxShadow: `0 0 6px ${colors[status] ?? "#4a4a68"}`,
    }} />
  );
}

function ReviewRow({ r, onDelete }: { r: ReviewListItem; onDelete: (id: string) => void }) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete review for "${r.repo_name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await deleteReview(r.id);
      onDelete(r.id);
    } catch {
      alert("Failed to delete review.");
      setDeleting(false);
    }
  };
  const grade = scoreGrade(r.overall_score);
  const color = scoreColor(r.overall_score);

  return (
    <div
      onClick={() => navigate(`/review/${r.id}`)}
      style={{
        display: "flex", alignItems: "center", gap: 16,
        padding: "14px 18px", borderRadius: 10,
        border: "1px solid rgba(255,255,255,0.05)",
        background: "rgba(255,255,255,0.01)",
        cursor: "pointer", transition: "all 0.15s",
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.03)";
        (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.09)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.01)";
        (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.05)";
      }}
    >
      {/* Grade */}
      <div className="font-display" style={{
        width: 36, height: 36, borderRadius: 8, flexShrink: 0,
        background: `${color}14`, border: `1px solid ${color}28`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "1rem", fontWeight: 800, color,
      }}>
        {grade}
      </div>

      {/* Repo info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "#e8e8f0", marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {r.repo_name}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="font-mono" style={{ fontSize: "0.65rem", color: "#6366f1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 260 }}>
            {r.repo_url.replace("https://github.com/", "")}
          </span>
          <span style={{ color: "#4a4a68", fontSize: "0.6rem" }}>·</span>
          <span style={{ fontSize: "0.65rem", color: "#6a6a88" }}>{r.user_email}</span>
        </div>
      </div>

      {/* Score breakdown (compact) */}
      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
        {[
          { label: "Sec",  v: r.security_score },
          { label: "Arch", v: r.architecture_score },
          { label: "Test", v: r.testing_score },
        ].map(({ label, v }) => (
          <div key={label} style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: scoreColor(v) }}>
              {v?.toFixed(0) ?? "—"}
            </div>
            <div style={{ fontSize: "0.55rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Status + time */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <StatusDot status={r.status} />
          <span style={{ fontSize: "0.7rem", color: "#6a6a88", textTransform: "capitalize" }}>{r.status}</span>
        </div>
        <span style={{ fontSize: "0.65rem", color: "#4a4a68" }}>{timeAgo(r.created_at)}</span>
      </div>

      {/* Delete button */}
      <button
        onClick={handleDelete}
        disabled={deleting}
        title="Delete review"
        style={{
          flexShrink: 0, width: 26, height: 26, borderRadius: 6,
          background: "transparent", border: "1px solid transparent",
          color: "#4a4a68", cursor: "pointer", display: "flex",
          alignItems: "center", justifyContent: "center",
          transition: "all 0.15s", opacity: deleting ? 0.4 : 1,
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.background = "rgba(239,68,68,0.1)";
          (e.currentTarget as HTMLButtonElement).style.color = "#f87171";
          (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(239,68,68,0.2)";
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.background = "transparent";
          (e.currentTarget as HTMLButtonElement).style.color = "#4a4a68";
          (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
        }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
        </svg>
      </button>

      {/* Arrow */}
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#4a4a68" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
        <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
      </svg>
    </div>
  );
}

function SkeletonRow() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 18px" }}>
      <div className="skeleton" style={{ width: 36, height: 36, borderRadius: 8, flexShrink: 0 }} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
        <div className="skeleton" style={{ height: 13, width: "40%" }} />
        <div className="skeleton" style={{ height: 10, width: "60%" }} />
      </div>
      <div className="skeleton" style={{ height: 13, width: 80 }} />
    </div>
  );
}

const SEV_COLORS: Record<string, string> = {
  critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#6366f1", info: "#6a6a88",
};

const SCORE_FIELDS = [
  { key: "security",     label: "Security" },
  { key: "architecture", label: "Arch" },
  { key: "testing",      label: "Testing" },
  { key: "scalability",  label: "Scale" },
  { key: "debt",         label: "Debt" },
] as const;

function OrgStats({ stats }: { stats: DashboardStats }) {
  const avg = stats.averages;
  const sev = stats.by_severity;
  const grade = stats.grade_distribution;

  const categoryData = stats.by_category.slice(0, 6).map((c) => ({
    name: c.category || "unknown",
    value: c.count,
  }));

  const scoreData = SCORE_FIELDS.map((f) => ({
    name: f.label,
    score: avg[f.key] ?? 0,
  }));

  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 14 }}>
        Org Health
      </div>

      {/* Stat tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
        {[
          { label: "Total Reviews",  value: stats.totals.reviews,          color: "#6366f1" },
          { label: "Repos Analyzed", value: stats.totals.repos,            color: "#8b5cf6" },
          { label: "Total Findings", value: stats.totals.findings,         color: "#f59e0b" },
          { label: "Avg Score",      value: avg.overall != null ? `${avg.overall}/100` : "—", color: scoreColor(avg.overall) },
        ].map((t) => (
          <div key={t.label} className="card" style={{ padding: "16px 18px" }}>
            <div style={{ fontSize: "1.3rem", fontWeight: 800, color: t.color, fontFamily: "Syne, sans-serif", marginBottom: 4 }}>
              {t.value}
            </div>
            <div style={{ fontSize: "0.65rem", color: "#6a6a88", textTransform: "uppercase", letterSpacing: "0.08em" }}>{t.label}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>

        {/* Avg score by dimension */}
        <div className="card" style={{ padding: "16px 18px" }}>
          <div style={{ fontSize: "0.65rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>Avg Score by Dimension</div>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={scoreData} margin={{ top: 0, right: 0, left: -24, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: "#6a6a88" }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#4a4a68" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#0e0e1a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: "0.75rem" }}
                labelStyle={{ color: "#e8e8f0" }}
                itemStyle={{ color: "#818cf8" }}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {scoreData.map((d) => (
                  <Cell key={d.name} fill={scoreColor(d.score)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Findings by category */}
        <div className="card" style={{ padding: "16px 18px" }}>
          <div style={{ fontSize: "0.65rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>Top Finding Categories</div>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={categoryData} layout="vertical" margin={{ top: 0, right: 0, left: 20, bottom: 0 }}>
              <XAxis type="number" tick={{ fontSize: 9, fill: "#4a4a68" }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: "#6a6a88" }} axisLine={false} tickLine={false} width={60} />
              <Tooltip
                contentStyle={{ background: "#0e0e1a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: "0.75rem" }}
                labelStyle={{ color: "#e8e8f0" }}
                itemStyle={{ color: "#818cf8" }}
              />
              <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Grade distribution + severity breakdown */}
        <div className="card" style={{ padding: "16px 18px" }}>
          <div style={{ fontSize: "0.65rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>Grade Distribution</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
            {(["A", "B", "C", "D"] as const).map((g) => {
              const colors = { A: "#22c55e", B: "#f59e0b", C: "#f97316", D: "#ef4444" };
              return (
                <div key={g} style={{
                  padding: "8px 10px", borderRadius: 8, textAlign: "center",
                  background: `${colors[g]}0d`, border: `1px solid ${colors[g]}22`,
                }}>
                  <div style={{ fontSize: "1rem", fontWeight: 800, color: colors[g], fontFamily: "Syne, sans-serif" }}>{grade[g] ?? 0}</div>
                  <div style={{ fontSize: "0.6rem", color: colors[g], opacity: 0.7 }}>Grade {g}</div>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: "0.65rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>By Severity</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {["critical", "high", "medium", "low"].map((s) => (
              <div key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: SEV_COLORS[s], flexShrink: 0 }} />
                <div style={{ fontSize: "0.7rem", color: "#6a6a88", textTransform: "capitalize", flex: 1 }}>{s}</div>
                <div style={{ fontSize: "0.7rem", fontWeight: 600, color: SEV_COLORS[s] }}>{sev[s] ?? 0}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Feedback summary */}
      {Object.keys(stats.feedback_summary).length > 0 && (
        <div className="card" style={{ padding: "14px 18px", marginTop: 10, display: "flex", gap: 24, alignItems: "center" }}>
          <div style={{ fontSize: "0.65rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.08em", flexShrink: 0 }}>Finding Feedback</div>
          {Object.entries(stats.feedback_summary).map(([action, count]) => {
            const colors: Record<string, string> = { confirmed: "#f87171", dismissed: "#94a3b8", fixed: "#4ade80" };
            return (
              <div key={action} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: colors[action] ?? "#6a6a88" }} />
                <span style={{ fontSize: "0.75rem", color: colors[action] ?? "#6a6a88", textTransform: "capitalize" }}>{action}</span>
                <span style={{ fontSize: "0.75rem", color: "#e8e8f0", fontWeight: 600 }}>{count}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listReviews(20).catch(() => [] as ReviewListItem[]),
      getDashboardStats().catch(() => null),
    ]).then(([r, s]) => {
      setReviews(r);
      setStats(s);
    }).finally(() => setLoading(false));
  }, []);

  const handleDelete = (id: string) => setReviews((prev) => prev.filter((r) => r.id !== id));

  return (
    <div className="bg-grid" style={{ minHeight: "100vh", padding: "40px 40px 60px" }}>
      {/* Header */}
      <div className="animate-fade-up" style={{ marginBottom: 36 }}>
        <h1 className="font-display" style={{ fontSize: "2rem", fontWeight: 800, color: "#e8e8f0", lineHeight: 1.1, marginBottom: 8 }}>
          Engineering Review<span style={{ color: "#6366f1" }}>.</span>
        </h1>
        <p style={{ fontSize: "0.875rem", color: "#8a8aaa" }}>
          Multi-agent AI code review — architecture, security, scalability, testing, debt, coaching
        </p>
      </div>

      {/* CTA */}
      <div className="animate-fade-up delay-1" style={{
        background: "linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(139,92,246,0.06) 100%)",
        border: "1px solid rgba(99,102,241,0.2)", borderRadius: 14,
        padding: "28px 32px", marginBottom: 32, position: "relative", overflow: "hidden",
      }}>
        <div style={{ position: "absolute", top: -50, right: -50, width: 200, height: 200, background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "relative" }}>
          <h2 className="font-display" style={{ fontSize: "1.125rem", fontWeight: 700, color: "#e8e8f0", marginBottom: 6 }}>
            Start a New Review
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "#8a8aaa", marginBottom: 18 }}>
            Paste a GitHub URL · 11 AI agents · full report in 5–15 minutes
          </p>
          <Link to="/review/new" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
            Run Analysis
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
            </svg>
          </Link>
        </div>
      </div>

      {/* Org stats — only shown when there's data */}
      {!loading && stats && stats.totals.complete_reviews > 0 && (
        <div className="animate-fade-up delay-2">
          <OrgStats stats={stats} />
        </div>
      )}

      {/* Recent reviews */}
      <div className="animate-fade-up delay-2" style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68" }}>
            Recent Reviews
          </div>
          {reviews.length > 0 && (
            <span style={{ fontSize: "0.7rem", color: "#6366f1" }}>{reviews.length} total</span>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {loading && [1, 2, 3].map(i => <SkeletonRow key={i} />)}

          {!loading && reviews.length === 0 && (
            <div style={{
              padding: "40px 24px", textAlign: "center",
              border: "1px dashed rgba(255,255,255,0.06)", borderRadius: 12,
            }}>
              <div style={{ fontSize: "1.75rem", marginBottom: 10, opacity: 0.3 }}>◈</div>
              <div style={{ fontSize: "0.875rem", color: "#8a8aaa", marginBottom: 4 }}>No reviews yet</div>
              <div style={{ fontSize: "0.75rem", color: "#4a4a68" }}>Submit your first repository above to get started.</div>
            </div>
          )}

          {!loading && reviews.map(r => <ReviewRow key={r.id} r={r} onDelete={handleDelete} />)}
        </div>
      </div>

      {/* Feature grid */}
      <div className="animate-fade-up delay-3">
        <div style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 14 }}>
          What gets analyzed
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="card card-hover" style={{ padding: "18px 20px" }}>
              <div style={{
                width: 30, height: 30, borderRadius: 7, background: f.bg, color: f.color,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "0.875rem", marginBottom: 10, border: `1px solid ${f.color}22`,
              }}>
                {f.icon}
              </div>
              <div className="font-display" style={{ fontSize: "0.8125rem", fontWeight: 600, color: "#e8e8f0", marginBottom: 4 }}>{f.title}</div>
              <div style={{ fontSize: "0.7rem", color: "#6a6a88", lineHeight: 1.55 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
