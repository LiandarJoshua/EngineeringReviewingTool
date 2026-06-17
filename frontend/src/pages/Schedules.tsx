import { useEffect, useState } from "react";
import { listSchedules, createSchedule, toggleSchedule, deleteSchedule } from "../api/client";
import type { Schedule } from "../api/client";

const INTERVALS = ["daily", "weekly", "monthly"] as const;

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [repoUrl, setRepoUrl] = useState("");
  const [email, setEmail] = useState("");
  const [interval, setInterval] = useState<"daily" | "weekly" | "monthly">("weekly");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setSchedules(await listSchedules());
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setCreating(true);
    setError("");
    try {
      await createSchedule(repoUrl.trim(), email.trim(), interval);
      setRepoUrl("");
      setEmail("");
      await load();
    } catch {
      setError("Failed to create schedule. Check the repo URL and try again.");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (id: string) => {
    await toggleSchedule(id);
    await load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this schedule?")) return;
    await deleteSchedule(id);
    await load();
  };

  return (
    <div style={{ padding: "36px 40px", maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#e8e8f0", fontFamily: "Syne, sans-serif", marginBottom: 6 }}>
          Scheduled Scans
        </h1>
        <p style={{ fontSize: "0.825rem", color: "#6a6a88" }}>
          Automatically re-run a full 11-stage review on a repo on a recurring schedule. Scores are tracked over time.
        </p>
      </div>

      {/* Create form */}
      <div className="card" style={{ padding: 24, marginBottom: 28 }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "#818cf8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 16 }}>
          New Schedule
        </div>
        <form onSubmit={handleCreate}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto", gap: 10, alignItems: "end" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.7rem", color: "#6a6a88", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                GitHub Repo URL
              </label>
              <input
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repo"
                style={{
                  width: "100%", padding: "9px 12px", borderRadius: 8,
                  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                  color: "#e8e8f0", fontSize: "0.825rem", outline: "none", boxSizing: "border-box",
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.7rem", color: "#6a6a88", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Email (optional)
              </label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                style={{
                  width: "100%", padding: "9px 12px", borderRadius: 8,
                  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                  color: "#e8e8f0", fontSize: "0.825rem", outline: "none", boxSizing: "border-box",
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.7rem", color: "#6a6a88", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Frequency
              </label>
              <select
                value={interval}
                onChange={(e) => setInterval(e.target.value as typeof interval)}
                style={{
                  padding: "9px 12px", borderRadius: 8,
                  background: "#0e0e1a", border: "1px solid rgba(255,255,255,0.08)",
                  color: "#e8e8f0", fontSize: "0.825rem", cursor: "pointer",
                }}
              >
                {INTERVALS.map((i) => <option key={i} value={i}>{i.charAt(0).toUpperCase() + i.slice(1)}</option>)}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating || !repoUrl.trim()}
              style={{
                padding: "9px 20px", borderRadius: 8, fontWeight: 600, fontSize: "0.8rem",
                background: creating || !repoUrl.trim() ? "rgba(99,102,241,0.3)" : "rgba(99,102,241,0.8)",
                color: "white", border: "none", cursor: creating || !repoUrl.trim() ? "default" : "pointer",
                transition: "background 0.15s",
              }}
            >
              {creating ? "Adding…" : "Add"}
            </button>
          </div>
          {error && <p style={{ color: "#f87171", fontSize: "0.75rem", marginTop: 10 }}>{error}</p>}
        </form>
      </div>

      {/* Schedule list */}
      {loading ? (
        <div style={{ color: "#4a4a68", fontSize: "0.85rem", textAlign: "center", padding: 40 }}>Loading…</div>
      ) : schedules.length === 0 ? (
        <div style={{
          padding: "60px 24px", textAlign: "center",
          border: "1px dashed rgba(255,255,255,0.06)", borderRadius: 12,
        }}>
          <div style={{ fontSize: "2rem", marginBottom: 12, opacity: 0.3 }}>⏱</div>
          <div style={{ color: "#6a6a88", fontSize: "0.875rem" }}>No scheduled scans yet</div>
          <div style={{ color: "#4a4a68", fontSize: "0.75rem", marginTop: 4 }}>Add a repo above to start automatic health monitoring</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {schedules.map((s) => (
            <div key={s.id} className="card" style={{ padding: "16px 20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                {/* Status dot */}
                <div style={{
                  width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                  background: s.is_active ? "#4ade80" : "#4a4a68",
                  boxShadow: s.is_active ? "0 0 6px rgba(74,222,128,0.5)" : "none",
                }} />

                {/* Repo info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#e8e8f0", marginBottom: 2 }}>
                    {s.repo_name}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#4a4a68", fontFamily: "monospace" }}>
                    {s.repo_url}
                  </div>
                </div>

                {/* Meta */}
                <div style={{ display: "flex", gap: 20, alignItems: "center", flexShrink: 0 }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.6rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>Frequency</div>
                    <div style={{ fontSize: "0.75rem", color: "#818cf8", fontWeight: 600, textTransform: "capitalize" }}>{s.interval_label}</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.6rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>Last Run</div>
                    <div style={{ fontSize: "0.75rem", color: "#8a8aaa" }}>{fmt(s.last_run_at)}</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.6rem", color: "#4a4a68", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>Next Run</div>
                    <div style={{ fontSize: "0.75rem", color: s.is_active ? "#e8e8f0" : "#4a4a68" }}>{fmt(s.next_run_at)}</div>
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <button
                    onClick={() => handleToggle(s.id)}
                    style={{
                      padding: "5px 14px", borderRadius: 99, fontSize: "0.7rem", fontWeight: 500,
                      cursor: "pointer", transition: "all 0.15s",
                      border: `1px solid ${s.is_active ? "rgba(74,222,128,0.3)" : "rgba(255,255,255,0.08)"}`,
                      background: s.is_active ? "rgba(74,222,128,0.08)" : "rgba(255,255,255,0.04)",
                      color: s.is_active ? "#4ade80" : "#6a6a88",
                    }}
                  >
                    {s.is_active ? "Pause" : "Resume"}
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    style={{
                      padding: "5px 14px", borderRadius: 99, fontSize: "0.7rem", fontWeight: 500,
                      cursor: "pointer", transition: "all 0.15s",
                      border: "1px solid rgba(239,68,68,0.2)",
                      background: "rgba(239,68,68,0.06)", color: "#f87171",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
