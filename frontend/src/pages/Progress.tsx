import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { getProgress } from "../api/client";

interface ProgressEntry {
  review_number: number;
  security: number;
  architecture: number;
  testing: number;
  scalability: number;
  overall: number;
}

const LINES = [
  { key: "overall",      label: "Overall",      color: "#6366f1" },
  { key: "security",     label: "Security",     color: "#ef4444" },
  { key: "architecture", label: "Architecture", color: "#3b82f6" },
  { key: "testing",      label: "Testing",      color: "#22c55e" },
  { key: "scalability",  label: "Scalability",  color: "#f59e0b" },
];

export default function Progress() {
  const { userId: paramUserId } = useParams<{ userId: string }>();
  const [userId,  setUserId]  = useState(paramUserId === "me" ? "" : (paramUserId ?? ""));
  const [repoId,  setRepoId]  = useState("");
  const [history, setHistory] = useState<ProgressEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  const handleLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setHistory(null); setLoading(true);
    try {
      const res = await getProgress(userId, repoId) as { history: ProgressEntry[] };
      setHistory(res.history ?? []);
    } catch {
      setError("Failed to load progress data. Check user ID and repo ID.");
    } finally {
      setLoading(false);
    }
  };

  const delta = history && history.length >= 2
    ? history[history.length - 1].overall - history[0].overall
    : null;

  return (
    <div style={{ padding: "40px", maxWidth: 900, margin: "0 auto" }}>
      {/* Header */}
      <div className="animate-fade-up" style={{ marginBottom: 32 }}>
        <div style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6366f1", marginBottom: 8 }}>
          Developer Tracking
        </div>
        <h1 className="font-display" style={{ fontSize: "1.875rem", fontWeight: 800, color: "#e8e8f0", lineHeight: 1.1, marginBottom: 8 }}>
          Progress Over Time
        </h1>
        <p style={{ fontSize: "0.875rem", color: "#8a8aaa", lineHeight: 1.6 }}>
          Track how scores evolve across multiple reviews of the same repository.
        </p>
      </div>

      {/* Form */}
      <div className="animate-fade-up delay-1 card" style={{ padding: "24px 28px", marginBottom: 24 }}>
        <form onSubmit={handleLoad}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 12, alignItems: "flex-end" }}>
            <div>
              <label className="field-label">Developer Email / User ID</label>
              <input
                required value={userId} onChange={(e) => setUserId(e.target.value)}
                placeholder="you@company.com or uuid"
                className="input-field"
              />
            </div>
            <div>
              <label className="field-label">Repository ID</label>
              <input
                required value={repoId} onChange={(e) => setRepoId(e.target.value)}
                placeholder="Repo UUID from a review"
                className="input-field font-mono"
                style={{ fontSize: "0.75rem" }}
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading} style={{ height: 38 }}>
              {loading ? "Loading…" : "Load"}
            </button>
          </div>
        </form>
        {error && (
          <div style={{
            marginTop: 14, padding: "10px 14px", borderRadius: 8,
            background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
            fontSize: "0.8rem", color: "#f87171",
          }}>
            {error}
          </div>
        )}
      </div>

      {/* Empty state */}
      {history !== null && history.length === 0 && (
        <div className="animate-fade-up card" style={{
          padding: "60px 24px", textAlign: "center",
          border: "1px dashed rgba(255,255,255,0.06)", background: "transparent",
        }}>
          <div style={{ fontSize: "2rem", marginBottom: 12, opacity: 0.3 }}>📈</div>
          <div style={{ fontSize: "0.9rem", color: "#8a8aaa", marginBottom: 4 }}>No history found</div>
          <div style={{ fontSize: "0.75rem", color: "#4a4a68" }}>
            Submit at least 2 reviews to this repo to start tracking progress.
          </div>
        </div>
      )}

      {/* Results */}
      {history && history.length > 0 && (
        <div className="animate-fade-up">
          {/* Summary tiles */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
            <div className="card" style={{ padding: "18px 20px", textAlign: "center" }}>
              <div className="font-display" style={{ fontSize: "2rem", fontWeight: 800, color: "#6366f1", lineHeight: 1 }}>
                {history.length}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#6a6a88", marginTop: 6 }}>Reviews submitted</div>
            </div>
            <div className="card" style={{ padding: "18px 20px", textAlign: "center" }}>
              <div className="font-display" style={{
                fontSize: "2rem", fontWeight: 800, lineHeight: 1,
                color: delta === null ? "#4a4a68" : delta >= 0 ? "#22c55e" : "#ef4444",
              }}>
                {delta === null ? "—" : `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}`}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#6a6a88", marginTop: 6 }}>Overall change</div>
            </div>
            <div className="card" style={{ padding: "18px 20px", textAlign: "center" }}>
              <div className="font-display" style={{ fontSize: "2rem", fontWeight: 800, color: "#e8e8f0", lineHeight: 1 }}>
                {history[history.length - 1].overall.toFixed(1)}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#6a6a88", marginTop: 6 }}>Current score</div>
            </div>
          </div>

          {/* Chart */}
          <div className="card" style={{ padding: "24px 20px", marginBottom: 16 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4a4a68", marginBottom: 20 }}>
              Score Trends · {history.length} review{history.length !== 1 ? "s" : ""}
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={history.map((h) => ({ ...h, name: `#${h.review_number}` }))}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="name" tick={{ fill: "#6a6a88", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fill: "#6a6a88", fontSize: 11 }} axisLine={false} tickLine={false} tickCount={6} />
                <Tooltip
                  contentStyle={{ background: "#111120", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#e8e8f0", fontWeight: 600 }}
                  formatter={(v: number) => [v.toFixed(1), ""]}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: "#8a8aaa", paddingTop: 16 }} />
                {LINES.map((l) => (
                  <Line key={l.key} type="monotone" dataKey={l.key} name={l.label}
                    stroke={l.color} strokeWidth={2} dot={{ r: 3, fill: l.color }} activeDot={{ r: 5 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    {["Review", ...LINES.map((l) => l.label)].map((h, i) => (
                      <th key={h} style={{
                        padding: "10px 16px", textAlign: i === 0 ? "left" : "right",
                        fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.08em",
                        textTransform: "uppercase", color: "#4a4a68",
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map((row, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                      <td className="font-mono" style={{ padding: "10px 16px", color: "#6a6a88", fontSize: "0.75rem" }}>
                        #{row.review_number}
                      </td>
                      {LINES.map((l) => {
                        const v = row[l.key as keyof ProgressEntry] as number;
                        const c = v >= 80 ? "#22c55e" : v >= 65 ? "#f59e0b" : "#ef4444";
                        return (
                          <td key={l.key} style={{ padding: "10px 16px", textAlign: "right", fontWeight: 600, color: c }}>
                            {v?.toFixed(1) ?? "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
