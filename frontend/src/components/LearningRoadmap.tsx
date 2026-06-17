interface Topic {
  topic: string;
  resource_type: string;
  reason: string;
}

interface CoachingReport {
  strengths?: unknown;
  priority_improvements?: unknown;
  learning_roadmap?: unknown;
  next_week_focus?: string;
  narrative?: string;
}

interface Props { report: CoachingReport | null | undefined; }

const RESOURCE_COLORS: Record<string, { bg: string; color: string }> = {
  book:    { bg: "rgba(139,92,246,0.1)", color: "#a78bfa" },
  course:  { bg: "rgba(6,182,212,0.1)",  color: "#22d3ee" },
  article: { bg: "rgba(34,197,94,0.1)",  color: "#4ade80" },
  video:   { bg: "rgba(245,158,11,0.1)", color: "#fbbf24" },
  default: { bg: "rgba(255,255,255,0.04)", color: "#8a8aaa" },
};

const RESOURCE_TYPES = RESOURCE_COLORS;

function ResourceTag({ type }: { type: string }) {
  const t = RESOURCE_TYPES[type?.toLowerCase()] ?? RESOURCE_COLORS.default;
  return (
    <span style={{
      fontSize: "0.6rem", fontWeight: 600, letterSpacing: "0.08em",
      textTransform: "uppercase", padding: "2px 8px", borderRadius: 99,
      background: t.bg, color: t.color,
    }}>
      {type}
    </span>
  );
}

export default function LearningRoadmap({ report }: Props) {
  // Safely coerce all list fields — LLMs can return strings, objects, null, or wrong types
  const toStringList = (val: unknown): string[] => {
    if (!Array.isArray(val)) return [];
    return val.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const o = item as Record<string, unknown>;
        const text = o.text ?? o.description ?? o.issue ?? o.improvement ??
                     o.step ?? o.action ?? o.title ?? o.content;
        const detail = o.steps ?? o.details ?? o.recommendation ?? o.reason;
        if (text) return detail ? `${text}: ${detail}` : String(text);
        return Object.values(o).filter(Boolean).join(", ");
      }
      return String(item);
    });
  };

  const strengths    = toStringList(report?.strengths);
  const improvements = toStringList(report?.priority_improvements);
  const roadmap      = Array.isArray(report?.learning_roadmap) ? (report!.learning_roadmap as Topic[]) : [];

  if (!report || (!report.narrative && !roadmap.length && !improvements.length && !strengths.length)) {
    return (
      <div style={{
        padding: "60px 24px", textAlign: "center",
        border: "1px dashed rgba(255,255,255,0.06)", borderRadius: 12,
      }}>
        <div style={{ fontSize: "2rem", marginBottom: 12, opacity: 0.3 }}>🎓</div>
        <div style={{ fontSize: "0.875rem", color: "#8a8aaa", marginBottom: 4 }}>
          Coaching report not available
        </div>
        <div style={{ fontSize: "0.75rem", color: "#4a4a68" }}>
          Complete a review to generate a personalized coaching plan.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* This week focus */}
      {report.next_week_focus && (
        <div style={{
          padding: "18px 20px", borderRadius: 12,
          background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)",
        }}>
          <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6366f1", marginBottom: 8 }}>
            This week's focus
          </div>
          <p style={{ fontSize: "0.875rem", color: "#c0c0d0", lineHeight: 1.65 }}>{report.next_week_focus}</p>
        </div>
      )}

      {/* Narrative */}
      {report.narrative && (
        <div className="card" style={{ padding: "20px 22px" }}>
          <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 10 }}>
            Coaching Summary
          </div>
          <p style={{ fontSize: "0.8125rem", color: "#c0c0d0", lineHeight: 1.7, whiteSpace: "pre-line" }}>
            {report.narrative}
          </p>
        </div>
      )}

      {/* Strengths & Improvements side by side */}
      {(strengths.length > 0 || improvements.length > 0) && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {strengths.length > 0 && (
            <div className="card" style={{ padding: "18px 20px" }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 12 }}>
                Strengths
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {strengths.map((s, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, fontSize: "0.8rem", color: "#c0c0d0", lineHeight: 1.5 }}>
                    <span style={{ color: "#22c55e", flexShrink: 0, marginTop: 1 }}>✓</span>
                    {String(s)}
                  </div>
                ))}
              </div>
            </div>
          )}
          {improvements.length > 0 && (
            <div className="card" style={{ padding: "18px 20px" }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 12 }}>
                Priority Improvements
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {improvements.map((item, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, fontSize: "0.8rem", color: "#c0c0d0", lineHeight: 1.5 }}>
                    <span style={{
                      flexShrink: 0, width: 18, height: 18, borderRadius: "50%",
                      background: "rgba(239,68,68,0.15)", color: "#f87171",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.6rem", fontWeight: 700, fontFamily: "JetBrains Mono, monospace",
                      marginTop: 1,
                    }}>
                      {i + 1}
                    </span>
                    {String(item)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Learning roadmap */}
      {roadmap.length > 0 && (
        <div>
          <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 12 }}>
            Learning Roadmap
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {roadmap.map((topic, i) => (
              <div key={i} className="card" style={{ padding: "14px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: topic.reason ? 6 : 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="font-mono" style={{ fontSize: "0.65rem", color: "#4a4a68", width: 20 }}>
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: "#e8e8f0" }}>{topic.topic}</span>
                  </div>
                  {topic.resource_type && <ResourceTag type={String(topic.resource_type)} />}
                </div>
                {topic.reason && (
                  <p style={{ fontSize: "0.75rem", color: "#6a6a88", lineHeight: 1.5, paddingLeft: 30 }}>
                    {topic.reason}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
