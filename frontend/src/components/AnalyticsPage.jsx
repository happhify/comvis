import { useEffect, useState } from "react";
import {
  getDailyStats,
  getHourlyStats,
  getDetectionHistory,
  getHistoryExportUrl,
} from "../services/api";
import DailyStats from "./DailyStats";

const PAGE_SIZE = 30;

function formatDateLong(dateText) {
  const d = new Date(`${dateText}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateText;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function todayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function fmtDur(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}
function statusClass(s) {
  const v = String(s || "").toLowerCase();
  return v === "verified" ? "green" : "red";
}
function badge(s) {
  const v = String(s || "").toLowerCase();
  return v === "verified" ? "EMPLOYEE" : "UNKNOWN";
}

function AnalyticsPage({ stats, control }) {
  const [daily, setDaily] = useState(null);
  const [hourly, setHourly] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        setDaily(await getDailyStats(14));
      } catch {
        setDaily(null);
      }
      try {
        setHourly(await getHourlyStats());
      } catch {
        setHourly(null);
      }
    }
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  // ---------- Detection History (digabung dari DetectionHistoryPage) ----------
  const [histDate, setHistDate] = useState(todayStr());
  const [histStatus, setHistStatus] = useState("all");
  const [offset, setOffset] = useState(0);
  const [histData, setHistData] = useState([]);
  const [histTotal, setHistTotal] = useState(0);
  const [histLoading, setHistLoading] = useState(true);
  const [histError, setHistError] = useState("");

  useEffect(() => {
    let alive = true;
    async function load() {
      setHistLoading(true);
      try {
        const res = await getDetectionHistory({
          date: histDate,
          status: histStatus,
          limit: PAGE_SIZE,
          offset,
        });
        if (!alive) return;
        setHistData(res.data ?? []);
        setHistTotal(res.total ?? 0);
        setHistError("");
      } catch (e) {
        if (alive) setHistError(e.message || "Failed to load history.");
      } finally {
        if (alive) setHistLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [histDate, histStatus, offset]);

  const histFrom = histTotal === 0 ? 0 : offset + 1;
  const histTo = Math.min(offset + PAGE_SIZE, histTotal);

  const dailyRows = daily?.data ?? [];
  const hourlyRows = hourly?.data ?? [];

  const last7 = dailyRows.slice(0, 7);
  const total7 = last7.reduce((sum, r) => sum + (r.count ?? 0), 0);
  const avg7 = last7.length > 0 ? Math.round(total7 / last7.length) : 0;

  const busiestDay = dailyRows.reduce(
    (best, r) => ((r.count ?? 0) > (best?.count ?? -1) ? r : best),
    null
  );

  const busiestHour = hourlyRows.reduce(
    (best, r) => ((r.count ?? 0) > (best?.count ?? -1) ? r : best),
    null
  );

  const maxHourCount = Math.max(1, ...hourlyRows.map((r) => r.count ?? 0));
  const detectionOn = control?.detection_enabled ?? true;

  return (
    <main className="analytics-main">
      <header className="main-header">
        <div className="header-left">
          <div className="header-camname">Analytics</div>
        </div>
      </header>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-value">{total7.toLocaleString("en-US")}</div>
          <div className="summary-label">People (last 7 days)</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{avg7.toLocaleString("en-US")}</div>
          <div className="summary-label">Average per day</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">
            {busiestDay ? formatDateLong(busiestDay.date) : "-"}
          </div>
          <div className="summary-label">
            Busiest day{busiestDay ? ` (${busiestDay.count} people)` : ""}
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-value">
            {busiestHour && busiestHour.count > 0 ? `${busiestHour.hour}:00` : "-"}
          </div>
          <div className="summary-label">
            Busiest hour today
            {busiestHour && busiestHour.count > 0 ? ` (${busiestHour.count} people)` : ""}
          </div>
        </div>
      </div>

      <div className="analytics-grid">
        <section className="panel-card">
          <h3 className="panel-title">
            People per Hour &middot; {hourly?.date ?? "today"}
          </h3>

          {hourlyRows.length === 0 ? (
            <div className="empty-note">
              {hourly?.message ?? "No hourly data yet."}
            </div>
          ) : (
            <>
              <div className="hour-chart">
                {hourlyRows.map((row) => (
                  <div
                    key={row.hour}
                    className="hour-col"
                    title={`${row.hour}:00 - ${row.count} people`}
                  >
                    <div
                      className={`hour-bar ${
                        busiestHour && row.hour === busiestHour.hour && row.count > 0
                          ? "max"
                          : ""
                      }`}
                      style={{
                        height: `${Math.max(2, (100 * (row.count ?? 0)) / maxHourCount)}%`,
                      }}
                    ></div>
                  </div>
                ))}
              </div>
              <div className="hour-labels">
                <span>00</span>
                <span>06</span>
                <span>12</span>
                <span>18</span>
                <span>23</span>
              </div>
            </>
          )}
        </section>

        <DailyStats daily={daily} />

        <section className="panel-card">
          <h3 className="panel-title">System Status</h3>
          <div className="sys-status-list">
            <div className="sys-row">
              <span>Camera</span>
              <strong>{stats?.camera_name ?? "-"}</strong>
            </div>
            <div className="sys-row">
              <span>Detection</span>
              <strong className={detectionOn ? "text-green" : "text-amber"}>
                {detectionOn ? "ACTIVE" : "INACTIVE"}
              </strong>
            </div>
            <div className="sys-row">
              <span>FPS</span>
              <strong>{Number(stats?.fps ?? 0).toFixed(1)}</strong>
            </div>
            <div className="sys-row">
              <span>People in frame</span>
              <strong>{stats?.people_in_frame ?? 0}</strong>
            </div>
            <div className="sys-row">
              <span>Total detections (session)</span>
              <strong>{(stats?.total_detections ?? 0).toLocaleString("en-US")}</strong>
            </div>
          </div>
        </section>
      </div>

      {/* ---------- Detection History ---------- */}
      <section className="panel-card">
        <h3 className="panel-title">Detection History</h3>

        <div className="history-filters">
          <label className="filter-field">
            <span>Date</span>
            <input
              className="login-input"
              type="date"
              value={histDate}
              onChange={(e) => {
                setOffset(0);
                setHistDate(e.target.value);
              }}
            />
          </label>
          <label className="filter-field">
            <span>Status</span>
            <select
              className="login-input"
              value={histStatus}
              onChange={(e) => {
                setOffset(0);
                setHistStatus(e.target.value);
              }}
            >
              <option value="all">All</option>
              <option value="verified">Employee</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <div className="filter-spacer" />
          <a
            className="btn-primary as-link"
            href={getHistoryExportUrl({ date: histDate, status: histStatus })}
            target="_blank"
            rel="noreferrer"
          >
            Export CSV
          </a>
        </div>

        {histError && <div className="users-alert error">{histError}</div>}

        {histLoading ? (
          <div className="empty-note">Loading…</div>
        ) : histData.length === 0 ? (
          <div className="empty-note">No events for this date/filter.</div>
        ) : (
          <>
            <table className="user-table history-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Frames</th>
                  <th>Camera</th>
                </tr>
              </thead>
              <tbody>
                {histData.map((s, i) => (
                  <tr key={`${s.first_seen}-${s.entry_id}-${i}`}>
                    <td>
                      {s.first_seen}
                      <span className="hist-out"> → {String(s.last_seen).slice(11)}</span>
                    </td>
                    <td>{fmtDur(s.duration_seconds)}</td>
                    <td>
                      <span className={`det-badge badge-${statusClass(s.identity_status)}`}>
                        {badge(s.identity_status)}
                      </span>
                    </td>
                    <td>{s.confidence > 0 ? `${Math.round(s.confidence * 100)}%` : "–"}</td>
                    <td className="user-created">{s.frames}</td>
                    <td className="user-created">{s.camera}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="history-pager">
              <span>
                {histFrom}–{histTo} of {histTotal.toLocaleString("en-US")} events
              </span>
              <div className="history-pager-btns">
                <button
                  className="btn-ghost"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </button>
                <button
                  className="btn-ghost"
                  disabled={histTo >= histTotal}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

export default AnalyticsPage;
