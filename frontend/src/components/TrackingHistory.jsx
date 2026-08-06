// ============================================================
// components/TrackingHistory.jsx
// Panel "Recent Activity" gaya VisionTrack: gabungan orang yang
// SEDANG dilacak (Active, dari stats.active_persons realtime) dan
// yang BARU SAJA selesai dilacak (Past, dari /api/detection-history
// hari ini). Menggantikan ActivePersons.jsx + RecentDetections.jsx.
// ============================================================

const PAST_LIMIT = 8;

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;

  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

// Nama + warna aksen berdasarkan IDENTITAS (Hadi / Unknown).
// Badge di kanan (ACTIVE/GONE) terpisah - itu soal masih dilacak atau tidak.
function identityInfo(status, label) {
  const s = String(status || "").toLowerCase();
  if (s === "verified") {
    const raw = String(label || "employee");
    const name = raw.charAt(0).toUpperCase() + raw.slice(1);
    return { name, cls: "green" };
  }
  return { name: "Unknown person", cls: "red" };
}

const INFO =
  "Active = currently tracked in frame. Past = recent sessions today that " +
  "already ended. Duration is counted from when a person starts being " +
  "tracked; if tracking breaks (occluded / walks away), the same person " +
  "may be counted again.";

function TrackingHistory({ activePersons, pastSessions }) {
  const active = Array.isArray(activePersons) ? activePersons : [];
  const activeIds = new Set(active.map((p) => p.entry_id));

  const past = (Array.isArray(pastSessions) ? pastSessions : [])
    .filter((s) => !activeIds.has(s.entry_id))
    .slice(0, PAST_LIMIT);

  return (
    <section className="panel-card">
      <h3 className="panel-title panel-title-row">
        <span>Recent Activity</span>
        <span className="info-dot" title={INFO} aria-label="Info">i</span>
      </h3>

      <div className="activity-group">
        <div className="activity-group-label">Active ({active.length})</div>
        {active.length === 0 ? (
          <div className="empty-note">No people in frame.</div>
        ) : (
          <div className="active-list">
            {active.map((p) => {
              const id = identityInfo(p.identity_status, p.identity_label);
              const conf = Number(p.recognition_confidence ?? 0);

              return (
                <div key={p.entry_id} className={`active-item ${id.cls}`}>
                  <div className="active-top">
                    <span className="active-name">{id.name}</span>
                    <span className="det-badge badge-green">ACTIVE</span>
                  </div>
                  <div className="active-sub">
                    <span>#{p.entry_id}</span>
                    <span>{p.first_seen}</span>
                    <span className="active-dur">
                      {formatDuration(p.duration_seconds)}
                    </span>
                    {conf > 0 && (
                      <span title="Model confidence in the label above, not similarity to Hadi">
                        conf {Math.round(conf * 100)}%
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="activity-group">
        <div className="activity-group-label">Past ({past.length})</div>
        {past.length === 0 ? (
          <div className="empty-note">No past activity yet today.</div>
        ) : (
          <div className="active-list">
            {past.map((s, i) => {
              const id = identityInfo(s.identity_status, s.identity_label);

              return (
                <div
                  key={`${s.entry_id ?? "x"}-${i}`}
                  className={`active-item ${id.cls} past`}
                >
                  <div className="active-top">
                    <span className="active-name">{id.name}</span>
                    <span className="det-badge badge-neutral">GONE</span>
                  </div>
                  <div className="active-sub">
                    <span>{String(s.first_seen).slice(11)}</span>
                    <span className="active-dur">
                      {formatDuration(s.duration_seconds)}
                    </span>
                    {s.confidence > 0 && (
                      <span>conf {Math.round(s.confidence * 100)}%</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

export default TrackingHistory;
