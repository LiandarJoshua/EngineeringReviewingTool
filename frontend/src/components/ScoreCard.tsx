import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  scores: {
    security?: number | null;
    architecture?: number | null;
    testing?: number | null;
    scalability?: number | null;
    debt?: number | null;
    overall?: number | null;
  };
}

const DIMS = [
  { key: "security",     label: "Security",      color: "#ef4444" },
  { key: "architecture", label: "Architecture",  color: "#6366f1" },
  { key: "testing",      label: "Testing",       color: "#22c55e" },
  { key: "scalability",  label: "Scalability",   color: "#f59e0b" },
  { key: "debt",         label: "Tech Debt",     color: "#8b5cf6" },
];

function scoreColor(v: number) {
  if (v >= 80) return "#22c55e";
  if (v >= 65) return "#f59e0b";
  if (v >= 50) return "#f97316";
  return "#ef4444";
}

function scoreGrade(v: number) {
  if (v >= 80) return "A";
  if (v >= 65) return "B";
  if (v >= 50) return "C";
  return "D";
}

export default function ScoreCard({ scores }: Props) {
  const overall = scores.overall ?? 0;
  const grade   = scoreGrade(overall);
  const color   = scoreColor(overall);

  const radarData = DIMS.map((d) => ({
    subject: d.label,
    value: scores[d.key as keyof typeof scores] ?? 0,
  }));

  return (
    <div className="card" style={{ padding: "28px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 6 }}>
            Overall Score
          </div>
          <div className="font-display" style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span style={{ fontSize: "3.5rem", fontWeight: 800, color, lineHeight: 1 }}>{grade}</span>
            <span style={{ fontSize: "1.25rem", fontWeight: 600, color: "#4a4a68" }}>
              {overall.toFixed(1)}<span style={{ fontSize: "0.875rem" }}>/100</span>
            </span>
          </div>
        </div>
        <div style={{
          background: `${color}18`, border: `1px solid ${color}30`,
          borderRadius: 8, padding: "6px 12px", fontSize: "0.75rem", color,
          fontWeight: 600,
        }}>
          {overall >= 80 ? "Excellent" : overall >= 65 ? "Good" : overall >= 50 ? "Needs Work" : "Critical Issues"}
        </div>
      </div>

      {/* Radar */}
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
          <PolarGrid stroke="rgba(255,255,255,0.06)" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#6a6a88", fontSize: 11, fontFamily: "DM Sans, sans-serif" }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#4a4a68", fontSize: 9 }} tickCount={4} />
          <Radar name="Score" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} strokeWidth={1.5} />
          <Tooltip
            contentStyle={{ background: "#111120", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#e8e8f0", fontWeight: 600 }}
            itemStyle={{ color: "#8a8aaa" }}
            formatter={(v: number) => [`${v.toFixed(0)}/100`, "Score"]}
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* Score tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8, marginTop: 4 }}>
        {DIMS.map((d) => {
          const val = scores[d.key as keyof typeof scores] ?? 0;
          const c   = scoreColor(val);
          return (
            <div key={d.key} style={{
              background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)",
              borderRadius: 8, padding: "10px 8px", textAlign: "center",
            }}>
              <div className="font-display" style={{ fontSize: "1.375rem", fontWeight: 700, color: c, lineHeight: 1 }}>
                {val.toFixed(0)}
              </div>
              <div style={{ fontSize: "0.65rem", color: "#6a6a88", marginTop: 4, letterSpacing: "0.02em" }}>
                {d.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
