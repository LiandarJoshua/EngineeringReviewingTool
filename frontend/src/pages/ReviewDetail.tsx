import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getReview, getFindings, cancelReview, generateCoaching } from "../api/client";
import type { ReviewResponse, Finding } from "../api/client";
import ScoreCard from "../components/ScoreCard";
import FindingsTable from "../components/FindingsTable";
import LearningRoadmap from "../components/LearningRoadmap";

type Tab = "overview" | "security" | "architecture" | "findings" | "coaching";

const TABS: { key: Tab; label: string; getCount?: (f: Finding[], r: ReviewResponse | null) => number | null }[] = [
  { key: "overview",      label: "Overview" },
  { key: "security",      label: "Security",     getCount: (f) => f.filter(x => x.agent_name === "semgrep" || x.agent_name === "bandit" || x.agent_name === "security_llm").length },
  { key: "architecture",  label: "Architecture", getCount: (f) => f.filter(x => x.agent_name === "architecture").length },
  { key: "findings",      label: "All Findings", getCount: (f) => f.length },
  { key: "coaching",      label: "Coaching" },
];

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string; border: string; dot: string }> = {
    complete: { bg: "rgba(34,197,94,0.08)",  color: "#22c55e", border: "rgba(34,197,94,0.2)",  dot: "#22c55e" },
    failed:   { bg: "rgba(239,68,68,0.08)",  color: "#f87171", border: "rgba(239,68,68,0.2)",  dot: "#ef4444" },
    pending:  { bg: "rgba(245,158,11,0.08)", color: "#fbbf24", border: "rgba(245,158,11,0.2)", dot: "#f59e0b" },
    running:  { bg: "rgba(99,102,241,0.08)", color: "#818cf8", border: "rgba(99,102,241,0.2)", dot: "#6366f1" },
  };
  const s = styles[status] ?? styles.pending;
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px",
      borderRadius: 99, background: s.bg, border: `1px solid ${s.border}`,
    }}>
      <div style={{
        width: 6, height: 6, borderRadius: "50%", background: s.dot, flexShrink: 0,
        boxShadow: `0 0 6px ${s.dot}`,
        animation: status === "running" ? "pulseDot 1.2s ease-in-out infinite" : "none",
      }} />
      <span style={{ fontSize: "0.7rem", fontWeight: 600, color: s.color, textTransform: "capitalize" }}>
        {status}
      </span>
    </div>
  );
}

function Skeleton({ h = 24, w = "100%" }: { h?: number; w?: string }) {
  return <div className="skeleton" style={{ height: h, width: w }} />;
}

export default function ReviewDetail() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();
  const [review,   setReview]   = useState<ReviewResponse | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [tab,      setTab]      = useState<Tab>("overview");
  const [loading,         setLoading]         = useState(true);
  const [error,           setError]           = useState("");
  const [cancelling,      setCancelling]      = useState(false);
  const [coachingLoading, setCoachingLoading] = useState(false);
  const [coachingQueued,  setCoachingQueued]  = useState(false);

  useEffect(() => {
    if (!reviewId) return;
    Promise.all([getReview(reviewId), getFindings(reviewId)])
      .then(([r, f]) => { setReview(r); setFindings(f); })
      .catch(() => setError("Failed to load review."))
      .finally(() => setLoading(false));
  }, [reviewId]);

  const handleCancel = async () => {
    if (!reviewId || !confirm("Cancel this review? The pipeline will stop.")) return;
    setCancelling(true);
    try {
      await cancelReview(reviewId);
      setReview((r) => r ? { ...r, status: "cancelled" } : r);
    } catch {
      alert("Failed to cancel.");
    } finally {
      setCancelling(false);
    }
  };

  const handleGenerateCoaching = async () => {
    if (!reviewId) return;
    setCoachingLoading(true);
    try {
      await generateCoaching(reviewId);
      setCoachingQueued(true);
    } catch {
      alert("Failed to start coaching generation.");
    } finally {
      setCoachingLoading(false);
    }
  };

  const secFindings  = findings.filter((f) => ["semgrep","bandit","security_llm"].includes(f.agent_name ?? ""));
  const archFindings = findings.filter((f) => f.agent_name === "architecture");
  const critCount    = findings.filter((f) => f.severity === "critical").length;
  const highCount    = findings.filter((f) => f.severity === "high").length;
  const medCount     = findings.filter((f) => f.severity === "medium").length;

  if (loading) return (
    <div style={{ padding: "40px", maxWidth: 900, margin: "0 auto" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Skeleton h={28} w="40%" />
        <Skeleton h={320} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
          {[1,2,3,4].map(i => <Skeleton key={i} h={80} />)}
        </div>
      </div>
    </div>
  );

  if (error || !review) return (
    <div style={{ padding: "40px" }}>
      <div style={{
        padding: "20px 24px", borderRadius: 12,
        background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
        color: "#f87171", fontSize: "0.875rem",
      }}>
        {error || "Review not found."}
      </div>
    </div>
  );

  return (
    <div style={{ padding: "40px", maxWidth: 900, margin: "0 auto" }}>
      {/* Header */}
      <div className="animate-fade-up" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <button onClick={() => navigate("/")} className="btn-ghost" style={{ fontSize: "0.75rem", padding: "4px 10px" }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
            </svg>
            Dashboard
          </button>
          <span style={{ color: "#4a4a68", fontSize: "0.75rem" }}>/</span>
          <span className="font-mono" style={{ fontSize: "0.75rem", color: "#6a6a88" }}>
            {reviewId?.slice(0, 8)}…
          </span>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <StatusPill status={review.status} />
            {["pending", "running"].includes(review.status) && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                style={{
                  padding: "4px 10px", borderRadius: 6, fontSize: "0.7rem", fontWeight: 600,
                  background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)",
                  color: "#f87171", cursor: "pointer", transition: "all 0.15s",
                  opacity: cancelling ? 0.5 : 1,
                }}
              >
                {cancelling ? "Cancelling…" : "Cancel"}
              </button>
            )}
          </div>
        </div>

        {/* Alert banner */}
        {(critCount > 0 || highCount > 0) && (
          <div style={{
            display: "flex", alignItems: "center", gap: 16, padding: "12px 16px",
            borderRadius: 10, marginBottom: 20,
            background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.18)",
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <div style={{ display: "flex", gap: 16 }}>
              {critCount > 0 && (
                <span style={{ fontSize: "0.8rem", color: "#f87171" }}>
                  <strong>{critCount}</strong> critical {critCount === 1 ? "issue" : "issues"}
                </span>
              )}
              {highCount > 0 && (
                <span style={{ fontSize: "0.8rem", color: "#fb923c" }}>
                  <strong>{highCount}</strong> high severity
                </span>
              )}
            </div>
            <span style={{ marginLeft: "auto", fontSize: "0.7rem", color: "#6a6a88" }}>
              Requires immediate attention
            </span>
          </div>
        )}

        {/* Tab nav */}
        <div style={{
          display: "flex", gap: 2, padding: "4px",
          background: "#111120", border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 10, overflowX: "auto",
        }}>
          {TABS.map((t) => {
            const count = t.getCount?.(findings, review);
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                style={{
                  flex: 1, padding: "7px 10px", borderRadius: 7, fontSize: "0.8rem",
                  fontWeight: 500, cursor: "pointer", border: "none",
                  transition: "all 0.15s", whiteSpace: "nowrap",
                  background: tab === t.key ? "rgba(99,102,241,0.12)" : "transparent",
                  color: tab === t.key ? "#818cf8" : "#6a6a88",
                  fontFamily: "DM Sans, sans-serif",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                }}
              >
                {t.label}
                {count != null && count > 0 && (
                  <span style={{
                    fontSize: "0.65rem", fontWeight: 700,
                    background: tab === t.key ? "rgba(99,102,241,0.25)" : "rgba(255,255,255,0.06)",
                    color: tab === t.key ? "#818cf8" : "#6a6a88",
                    padding: "1px 6px", borderRadius: 99,
                  }}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="animate-fade-up delay-1">
        {tab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <ScoreCard scores={{
              security: review.security_score,
              architecture: review.architecture_score,
              testing: review.testing_score,
              scalability: review.scalability_score,
              debt: review.debt_score,
              overall: review.overall_score,
            }} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              {[
                { label: "Critical", value: critCount,     color: "#f87171", bg: "rgba(239,68,68,0.08)"  },
                { label: "High",     value: highCount,     color: "#fb923c", bg: "rgba(249,115,22,0.08)" },
                { label: "Medium",   value: medCount,      color: "#fbbf24", bg: "rgba(245,158,11,0.08)" },
                { label: "Total",    value: findings.length, color: "#e8e8f0", bg: "rgba(255,255,255,0.03)" },
              ].map((stat) => (
                <div key={stat.label} className="card" style={{ padding: "18px 16px", textAlign: "center", background: stat.bg }}>
                  <div className="font-display" style={{ fontSize: "2rem", fontWeight: 800, color: stat.color, lineHeight: 1 }}>
                    {stat.value}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#6a6a88", marginTop: 6 }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {tab === "security"     && <FindingsTable findings={secFindings} />}
        {tab === "architecture" && <FindingsTable findings={archFindings} />}
        {tab === "findings"     && <FindingsTable findings={findings} />}
        {tab === "coaching" && (
          <div>
            {!review.coaching_report && !coachingQueued && review.status === "complete" && (
              <div style={{
                padding: "24px 28px", marginBottom: 20, borderRadius: 12,
                background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.18)",
                display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
              }}>
                <div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#e8e8f0", marginBottom: 4 }}>
                    Coaching report not generated
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#8a8aaa" }}>
                    Generate a personalized learning roadmap based on the findings from this review.
                  </div>
                </div>
                <button
                  onClick={handleGenerateCoaching}
                  disabled={coachingLoading}
                  className="btn-primary"
                  style={{ flexShrink: 0, fontSize: "0.8rem" }}
                >
                  {coachingLoading ? (
                    <>
                      <div style={{ width: 12, height: 12, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white", borderRadius: "50%" }} className="animate-spin-slow" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                      </svg>
                      Generate Coaching Report
                    </>
                  )}
                </button>
              </div>
            )}
            {coachingQueued && !review.coaching_report && (
              <div style={{
                padding: "16px 20px", marginBottom: 20, borderRadius: 10,
                background: "rgba(34,197,94,0.07)", border: "1px solid rgba(34,197,94,0.2)",
                fontSize: "0.8rem", color: "#4ade80",
              }}>
                Coaching report is being generated. Refresh this page in ~30 seconds to see it.
              </div>
            )}
            <LearningRoadmap report={review.coaching_report ?? null} />
          </div>
        )}
      </div>
    </div>
  );
}
