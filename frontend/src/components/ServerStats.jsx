// ============================================================
// components/ServerStats.jsx
// Progress bar CPU / RAM / Disk / GPU / VRAM.
// Bentuk data mengikuti backend/server_monitor.py.
// Kalau GPU tidak terbaca (available: false), tampilkan N/A.
// ============================================================

function toPercent(value) {
  if (value === null || value === undefined) return null;
  const n = parseFloat(value);
  if (Number.isNaN(n)) return null;
  return Math.min(100, Math.max(0, n));
}

// Warna bar sesuai beban: hijau < 60, kuning < 85, merah >= 85
function barClass(percent) {
  if (percent === null) return "na";
  if (percent < 60) return "ok";
  if (percent < 85) return "warn";
  return "crit";
}

function ServerStats({ data }) {
  const gpu = data?.gpu;

  let vramPercent = null;
  let vramDetail = null;
  if (gpu?.available && gpu.vram_used_gb != null && gpu.vram_total_gb > 0) {
    vramPercent = toPercent((gpu.vram_used_gb / gpu.vram_total_gb) * 100);
    vramDetail = `${gpu.vram_used_gb} / ${gpu.vram_total_gb} GB`;
  }

  let gpuDetail = null;
  if (gpu?.available) {
    gpuDetail = gpu.name;
    if (gpu.temperature != null) {
      gpuDetail += ` · ${gpu.temperature}°C`;
    }
  }

  const rows = [
    {
      name: "CPU",
      percent: toPercent(data?.cpu?.percent),
    },
    {
      name: "RAM",
      percent: toPercent(data?.ram?.percent),
      detail: data?.ram
        ? `${data.ram.used_gb} / ${data.ram.total_gb} GB`
        : null,
    },
    {
      name: "Disk",
      percent: toPercent(data?.disk?.percent),
      detail: data?.disk
        ? `${data.disk.used_gb} / ${data.disk.total_gb} GB`
        : null,
    },
    {
      name: "GPU",
      percent: gpu?.available ? toPercent(gpu.gpu_percent) : null,
      detail: gpuDetail,
    },
    {
      name: "VRAM",
      percent: vramPercent,
      detail: vramDetail,
    },
  ];

  return (
    <section className="panel-card">
      <h3 className="panel-title">Server Monitoring</h3>

      {!data ? (
        <div className="empty-note">
          Backend offline. Server data unavailable.
        </div>
      ) : (
        <div className="server-list">
          {rows.map((row) => (
            <div key={row.name}>
              <div className="server-row-head">
                <span className="server-name">{row.name}</span>
                <span className="server-value">
                  {row.percent === null ? "N/A" : `${row.percent.toFixed(0)}%`}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className={`progress-fill ${barClass(row.percent)}`}
                  style={{ width: `${row.percent ?? 0}%` }}
                ></div>
              </div>
              {row.detail && <div className="server-detail">{row.detail}</div>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default ServerStats;