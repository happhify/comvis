// ============================================================
// components/DetectionStats.jsx
// Tiga kartu angka: Employee, Unknown, Unique people.
// Nilai diambil dari /api/stats (dikirim main.py).
// "?? 0" artinya: kalau datanya belum ada, tampilkan 0.
// ============================================================

function DetectionStats({ stats }) {
  const cards = [
    {
      label: "Active employees",
      value: stats?.employee_active ?? 0,
    },
    {
      label: "Active unknown",
      value: stats?.unknown_active ?? 0,
    },
    {
      // "Total detections" pindah ke chip header (angkanya per-baris log,
      // membingungkan sebagai kartu). Kartu ini diganti perkiraan
      // jumlah ORANG unik dari recognition cache di main.py.
      label: "Unique people (sessions, ±)",
      value: (stats?.unique_persons ?? 0).toLocaleString("en-US"),
    },
  ];

  return (
    <section className="panel-card">
      <h3 className="panel-title">Detection Stats</h3>
      <div className="stats-grid">
        {cards.map((card) => (
          <div key={card.label} className="stat-card">
            <div className="stat-value">{card.value}</div>
            <div className="stat-label">{card.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default DetectionStats;