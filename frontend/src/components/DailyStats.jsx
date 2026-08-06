// ============================================================
// components/DailyStats.jsx  (Tahap Database)
// Rekap jumlah orang terdeteksi per hari, dari /api/daily-stats
// (sumber: SQLite outputs/comvis_stats.db yang diisi main.py).
// Tampil sebagai daftar tanggal + bar horizontal sederhana.
// ============================================================

// "2026-07-13" -> "Mon, Jul 13"
function formatDate(dateText) {
  const d = new Date(`${dateText}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateText;
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function DailyStats({ daily }) {
  const rows = daily?.data ?? [];

  // Nilai terbesar dipakai sebagai patokan panjang bar (100%)
  const maxCount = Math.max(1, ...rows.map((r) => r.count ?? 0));

  return (
    <section className="panel-card">
      <h3 className="panel-title">People per Day</h3>

      {rows.length === 0 ? (
        <div className="empty-note">
          {daily?.message ?? "No daily data yet."}
        </div>
      ) : (
        <div className="daily-list">
          {rows.map((row) => (
            <div key={row.date} className="daily-row">
              <span className="daily-date">{formatDate(row.date)}</span>
              <div className="daily-bar-track">
                <div
                  className="daily-bar-fill"
                  style={{ width: `${(100 * (row.count ?? 0)) / maxCount}%` }}
                ></div>
              </div>
              <span className="daily-count">
                {(row.count ?? 0).toLocaleString("en-US")}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="daily-note">
        Estimated unique people per day (someone entering and leaving over a
        long period may be counted more than once).
      </div>
    </section>
  );
}

export default DailyStats;