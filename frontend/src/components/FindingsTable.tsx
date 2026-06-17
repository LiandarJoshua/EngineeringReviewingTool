import { useState } from "react";
import type { Finding, FeedbackAction } from "../api/client";
import { submitFeedback } from "../api/client";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;
type Severity = typeof SEVERITY_ORDER[number];

const BADGE_CLASS: Record<string, string> = {
  critical: "badge-critical",
  high:     "badge-high",
  medium:   "badge-medium",
  low:      "badge-low",
  info:     "badge-info",
};

const SEVERITY_SORT: Record<string, number> = {
  critical: 0, high: 1, medium: 2, low: 3, info: 4,
};

interface Props { findings: Finding[]; }

const FEEDBACK_LABELS: Record<FeedbackAction, { label: string; color: string; bg: string; border: string }> = {
  confirmed:  { label: "Confirmed",   color: "#f87171", bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.2)" },
  dismissed:  { label: "False positive", color: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.2)" },
  fixed:      { label: "Fixed",       color: "#4ade80", bg: "rgba(74,222,128,0.08)",  border: "rgba(74,222,128,0.2)" },
};

function FeedbackBar({ findingId }: { findingId: string }) {
  const [current, setCurrent] = useState<FeedbackAction | null>(null);
  const [saving, setSaving] = useState(false);

  const handle = async (action: FeedbackAction) => {
    if (saving) return;
    const next = current === action ? null : action;
    setSaving(true);
    try {
      if (next) await submitFeedback(findingId, next);
      setCurrent(next);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 8 }}>
        Feedback
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {(Object.entries(FEEDBACK_LABELS) as [FeedbackAction, typeof FEEDBACK_LABELS[FeedbackAction]][]).map(([action, style]) => {
          const active = current === action;
          return (
            <button
              key={action}
              onClick={() => handle(action)}
              disabled={saving}
              style={{
                padding: "4px 12px", borderRadius: 99, fontSize: "0.7rem", fontWeight: 500,
                cursor: saving ? "default" : "pointer", transition: "all 0.15s",
                border: `1px solid ${active ? style.border : "rgba(255,255,255,0.08)"}`,
                background: active ? style.bg : "transparent",
                color: active ? style.color : "#6a6a88",
                opacity: saving ? 0.6 : 1,
              }}
            >
              {active ? "✓ " : ""}{style.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function FindingsTable({ findings }: Props) {
  const [filter,   setFilter]   = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const sorted = [...findings].sort(
    (a, b) => (SEVERITY_SORT[a.severity ?? "info"] ?? 4) - (SEVERITY_SORT[b.severity ?? "info"] ?? 4)
  );
  const filtered = filter === "all" ? sorted : sorted.filter((f) => f.severity === filter);

  const counts = SEVERITY_ORDER.reduce<Record<string, number>>((acc, s) => {
    acc[s] = findings.filter((f) => f.severity === s).length;
    return acc;
  }, {});

  if (findings.length === 0) {
    return (
      <div style={{
        padding: "60px 24px", textAlign: "center",
        border: "1px dashed rgba(255,255,255,0.06)", borderRadius: 12,
      }}>
        <div style={{ fontSize: "2rem", marginBottom: 12, opacity: 0.4 }}>✓</div>
        <div style={{ fontSize: "0.9rem", color: "#8a8aaa", fontWeight: 500, marginBottom: 4 }}>
          No findings in this category
        </div>
        <div style={{ fontSize: "0.75rem", color: "#4a4a68" }}>
          Either the code is clean or this agent found nothing to flag.
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Filter bar */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
        <button
          onClick={() => setFilter("all")}
          style={{
            padding: "5px 12px", borderRadius: 99, fontSize: "0.75rem", fontWeight: 500,
            border: `1px solid ${filter === "all" ? "rgba(99,102,241,0.4)" : "rgba(255,255,255,0.06)"}`,
            background: filter === "all" ? "rgba(99,102,241,0.12)" : "transparent",
            color: filter === "all" ? "#818cf8" : "#6a6a88",
            cursor: "pointer", transition: "all 0.15s",
          }}
        >
          All ({findings.length})
        </button>
        {SEVERITY_ORDER.map((s) =>
          counts[s] > 0 ? (
            <button
              key={s}
              onClick={() => setFilter(s)}
              style={{
                padding: "5px 12px", borderRadius: 99, fontSize: "0.75rem",
                fontWeight: 500, cursor: "pointer", transition: "all 0.15s",
                border: "1px solid rgba(255,255,255,0.06)",
                background: filter === s ? "rgba(255,255,255,0.06)" : "transparent",
                color: filter === s ? "#e8e8f0" : "#6a6a88",
                textTransform: "capitalize",
              }}
            >
              {s} ({counts[s]})
            </button>
          ) : null
        )}
      </div>

      {/* Findings */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {filtered.length === 0 && (
          <div style={{ padding: "24px", textAlign: "center", color: "#4a4a68", fontSize: "0.8rem" }}>
            No {filter} findings.
          </div>
        )}
        {filtered.map((f) => (
          <div
            key={f.id}
            className="card"
            style={{ overflow: "hidden", transition: "border-color 0.15s" }}
          >
            <button
              style={{
                width: "100%", textAlign: "left", padding: "14px 18px",
                display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer",
                background: "transparent", border: "none", color: "inherit",
              }}
              onClick={() => setExpanded(expanded === f.id ? null : f.id)}
            >
              <span className={BADGE_CLASS[f.severity ?? "info"] || "badge-info"} style={{ marginTop: 1, flexShrink: 0 }}>
                {f.severity ?? "info"}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: "0.8125rem", color: "#e8e8f0", fontWeight: 500,
                  marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {f.issue}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {f.file_path && (
                    <span className="font-mono" style={{ fontSize: "0.65rem", color: "#6366f1" }}>
                      {f.file_path}{f.line_number ? `:${f.line_number}` : ""}
                    </span>
                  )}
                  {f.agent_name && (
                    <span style={{
                      fontSize: "0.6rem", color: "#4a4a68",
                      background: "rgba(255,255,255,0.04)", padding: "1px 6px",
                      borderRadius: 99, border: "1px solid rgba(255,255,255,0.05)",
                    }}>
                      {f.agent_name}
                    </span>
                  )}
                </div>
              </div>
              <span style={{ color: "#4a4a68", fontSize: "0.7rem", flexShrink: 0, marginTop: 2 }}>
                {expanded === f.id ? "▲" : "▼"}
              </span>
            </button>

            {expanded === f.id && (
              <div style={{
                padding: "0 18px 16px", borderTop: "1px solid rgba(255,255,255,0.05)",
                display: "flex", flexDirection: "column", gap: 14, marginTop: 0, paddingTop: 14,
              }}>
                <div>
                  <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 6 }}>
                    Issue
                  </div>
                  <p style={{ fontSize: "0.8125rem", color: "#c0c0d0", lineHeight: 1.6 }}>{f.issue}</p>
                </div>
                {f.recommendation && (
                  <div>
                    <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 6 }}>
                      Recommendation
                    </div>
                    <p style={{
                      fontSize: "0.8125rem", color: "#4ade80", lineHeight: 1.6,
                      padding: "10px 12px", borderRadius: 8,
                      background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.12)",
                    }}>
                      {f.recommendation}
                    </p>
                  </div>
                )}
                {f.file_path && (
                  <div>
                    <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 6 }}>
                      Location
                    </div>
                    <code className="font-mono" style={{
                      fontSize: "0.75rem", color: "#818cf8",
                      background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.15)",
                      padding: "4px 10px", borderRadius: 6, display: "inline-block",
                    }}>
                      {f.file_path}{f.line_number ? `:${f.line_number}` : ""}
                    </code>
                  </div>
                )}
                <FeedbackBar findingId={f.id} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
