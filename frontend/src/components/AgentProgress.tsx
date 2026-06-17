import { useEffect, useState } from "react";
import { WS_URL } from "../api/client";

const STAGES = [
  { key: "ingestion",      label: "Clone & Stack Detection" },
  { key: "code_mapping",   label: "AST Code Mapping" },
  { key: "architecture",   label: "Architecture Analysis" },
  { key: "security",       label: "Security Audit" },
  { key: "scalability",    label: "Scalability Review" },
  { key: "testing",        label: "Testing Quality" },
  { key: "technical_debt", label: "Technical Debt" },
  { key: "requirements",   label: "Requirements Alignment" },
  { key: "coaching",       label: "Developer Coaching" },
  { key: "prioritization", label: "Prioritization" },
  { key: "synthesis",      label: "Final Report" },
];

type StageStatus = "pending" | "running" | "complete" | "skipped" | "failed";

interface Props {
  reviewId: string;
  onComplete?: () => void;
}

function StatusIcon({ status }: { status: StageStatus }) {
  if (status === "complete") return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
  if (status === "failed") return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
  if (status === "running") return (
    <div style={{
      width: 7, height: 7, borderRadius: "50%",
      background: "currentColor",
    }} className="animate-pulse-dot" />
  );
  return null;
}

function StageIndicator({ status, index }: { status: StageStatus; index: number }) {
  const styles: Record<StageStatus, { bg: string; color: string; border: string }> = {
    complete: { bg: "rgba(34,197,94,0.15)",  color: "#22c55e", border: "rgba(34,197,94,0.3)" },
    running:  { bg: "rgba(99,102,241,0.2)",  color: "#818cf8", border: "rgba(99,102,241,0.4)" },
    failed:   { bg: "rgba(239,68,68,0.15)",  color: "#f87171", border: "rgba(239,68,68,0.3)" },
    skipped:  { bg: "rgba(255,255,255,0.04)", color: "#4a4a68", border: "rgba(255,255,255,0.06)" },
    pending:  { bg: "rgba(255,255,255,0.04)", color: "#4a4a68", border: "rgba(255,255,255,0.06)" },
  };
  const s = styles[status];
  return (
    <div style={{
      width: 26, height: 26, borderRadius: "50%",
      background: s.bg, color: s.color,
      border: `1px solid ${s.border}`,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0,
      transition: "all 0.3s ease",
      boxShadow: status === "running" ? "0 0 12px rgba(99,102,241,0.3)" : "none",
    }}>
      {(status === "pending" || status === "skipped") ? (
        <span className="font-mono" style={{ fontSize: "0.6rem", color: s.color }}>
          {String(index + 1).padStart(2, "0")}
        </span>
      ) : (
        <StatusIcon status={status} />
      )}
    </div>
  );
}

export default function AgentProgress({ reviewId, onComplete }: Props) {
  const [statuses, setStatuses] = useState<Record<string, StageStatus>>(
    Object.fromEntries(STAGES.map((s) => [s.key, "pending"]))
  );
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/progress/${reviewId}`);
    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => {
      try {
        const { stage, status } = JSON.parse(event.data) as { stage: string; status: StageStatus };
        setStatuses((prev) => ({ ...prev, [stage]: status }));
        if (stage === "synthesis" && status === "complete") {
          ws.close();
          onComplete?.();
        }
      } catch {}
    };
    ws.onerror = () => { setConnected(false); ws.close(); };
    ws.onclose  = () => setConnected(false);
    return () => ws.close();
  }, [reviewId, onComplete]);

  const completedCount = Object.values(statuses).filter((s) => s === "complete").length;
  const failedCount    = Object.values(statuses).filter((s) => s === "failed").length;
  const progress = Math.round((completedCount / STAGES.length) * 100);

  return (
    <div className="card" style={{ padding: "24px 28px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h2 className="font-display" style={{ fontSize: "1rem", fontWeight: 700, color: "#e8e8f0", marginBottom: 2 }}>
            Analysis Pipeline
          </h2>
          <p style={{ fontSize: "0.75rem", color: "#8a8aaa" }}>
            {completedCount} of {STAGES.length} stages complete
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Connection dot */}
          <div style={{
            width: 7, height: 7, borderRadius: "50%",
            background: connected ? "#22c55e" : "#4a4a68",
            boxShadow: connected ? "0 0 6px rgba(34,197,94,0.5)" : "none",
            transition: "all 0.3s",
          }} />
          <span className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, color: "#6366f1" }}>
            {progress}%
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="progress-bar" style={{ marginBottom: 24 }}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      {/* Stages */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {STAGES.map((stage, i) => {
          const status = statuses[stage.key];
          return (
            <div
              key={stage.key}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "8px 10px", borderRadius: 8,
                background: status === "running" ? "rgba(99,102,241,0.06)" : "transparent",
                border: `1px solid ${status === "running" ? "rgba(99,102,241,0.15)" : "transparent"}`,
                transition: "all 0.2s",
              }}
            >
              <StageIndicator status={status} index={i} />
              <span style={{
                fontSize: "0.8125rem",
                color: status === "complete" ? "#8a8aaa"
                     : status === "running"  ? "#e8e8f0"
                     : status === "failed"   ? "#f87171"
                     : "#4a4a68",
                fontWeight: status === "running" ? 500 : 400,
                transition: "color 0.2s",
                textDecoration: status === "skipped" ? "line-through" : "none",
              }}>
                {stage.label}
              </span>
              {status === "running" && (
                <span style={{ marginLeft: "auto", fontSize: "0.7rem", color: "#818cf8" }}>
                  running…
                </span>
              )}
              {status === "failed" && (
                <span style={{ marginLeft: "auto", fontSize: "0.7rem", color: "#f87171" }}>
                  failed
                </span>
              )}
            </div>
          );
        })}
      </div>

      {failedCount > 0 && (
        <div style={{
          marginTop: 16, padding: "10px 14px", borderRadius: 8,
          background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
          fontSize: "0.75rem", color: "#f87171",
        }}>
          {failedCount} stage{failedCount > 1 ? "s" : ""} failed. Partial results are still available.
        </div>
      )}
    </div>
  );
}
