// ============================================================
// components/ModelQualityPage.jsx
// Halaman "Kualitas Model": menampilkan seberapa jauh model ini
// sudah diuji, apa adanya. Angka diambil dari file hasil evaluasi
// (negative_only_summary.csv / positive_test_summary.csv) dan
// ambang dari config/camera.yaml - tidak ada yang di-hardcode.
// ============================================================

import { useEffect, useState } from "react";
import { getModelQuality } from "../services/api";

function pct(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return `${(n * 100).toFixed(digits)}%`;
}

function num(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString("id-ID") : "-";
}

function Row({ label, value }) {
  return (
    <div className="sys-row">
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}

function ModelQualityPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setData(await getModelQuality());
        setError("");
      } catch (e) {
        setError(e.message || "Gagal memuat kualitas model.");
      }
    }
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  const verdict = data?.verdict;
  const neg = data?.negative_test;
  const pos = data?.positive_test;
  const th = data?.thresholds;

  return (
    <main className="quality-main">
      <header className="main-header">
        <div className="header-left">
          <div className="header-camname">Kualitas Model</div>
        </div>
      </header>

      {error && <div className="users-alert error">{error}</div>}

      {verdict && (
        <div className={`verdict-card ${verdict.level}`}>
          <div className="verdict-title">{verdict.title}</div>
          <div className="verdict-detail">{verdict.detail}</div>
          <div className="verdict-principle">{data.principle}</div>
        </div>
      )}

      <div className="quality-grid">
        {/* ---------- Negative-only test ---------- */}
        <section className="panel-card">
          <h3 className="panel-title">Negative-only Test &middot; target TIDAK di frame</h3>

          {!neg?.available ? (
            <div className="empty-note">
              Belum ada data pengujian untuk model saat ini.
            </div>
          ) : (
            <>
              <div className="quality-headline red">{pct(neg.false_positive_rate)}</div>
              <div className="quality-headline-label">
                False positive rate &mdash; {num(neg.false_positive_candidate)} dari{" "}
                {num(neg.total_rows)} baris deteksi
              </div>
              <div className="sys-status-list">
                <Row label="Dijalankan" value={neg.generated_at} />
                <Row label="Target" value={neg.target_label} />
                <Row label="Baris 'Verified target'" value={num(neg.verified_target_rows)} />
                <Row label="Status" value={neg.evaluation_status} />
              </div>
              <div className="daily-note">
                Periode pengujian: {neg.window_start} &rarr; {neg.window_end}.
                Mengukur seberapa sering sistem tetap memberi label "Verified"
                saat target sebenarnya tidak berada di depan kamera.
              </div>
            </>
          )}
        </section>

        {/* ---------- Positive test ---------- */}
        <section className="panel-card">
          <h3 className="panel-title">Positive Test &middot; target ADA di frame</h3>

          {!pos?.available ? (
            <div className="empty-note">
              Belum ada data pengujian untuk model saat ini.
            </div>
          ) : (
            <>
              <div className="quality-headline green">
                {pct(pos.verified_target_rate, 1)}
              </div>
              <div className="quality-headline-label">
                Berhasil Verified &mdash; {num(pos.verified_target_rows)} dari{" "}
                {num(pos.total_rows)} baris
              </div>
              <div className="sys-status-list">
                <Row label="Dijalankan" value={pos.generated_at} />
                <Row label="Jumlah jendela uji" value={pos.num_windows} />
                <Row label="Unverified" value={pct(pos.unverified_rate, 1)} />
                <Row label="Unknown" value={pct(pos.unknown_rate, 1)} />
                <Row label="Verified label salah" value={num(pos.verified_nontarget_rows)} />
                <Row label="Status" value={pos.evaluation_status} />
              </div>
              <div className="daily-note">
                Tingkat Unverified yang tinggi merupakan hasil yang diharapkan
                &mdash; sistem dirancang untuk tidak memberi label saat tidak
                yakin, dibanding berisiko salah mengenali.
              </div>
            </>
          )}
        </section>

        {/* ---------- Ambang ---------- */}
        <section className="panel-card">
          <h3 className="panel-title">Ambang yang Sedang Dipakai</h3>

          {!th?.available ? (
            <div className="empty-note">Konfigurasi ambang tidak dapat dimuat.</div>
          ) : (
            <>
              <div className="sys-status-list">
                <Row label="Verified threshold" value={th.verified_threshold} />
                <Row label="Unknown threshold" value={th.unknown_threshold} />
                <Row label="Min margin" value={th.min_margin} />
                <Row
                  label="Min ukuran crop"
                  value={`${th.min_crop_width} x ${th.min_crop_height} px`}
                />
                <Row label="Confidence detektor" value={th.detection_confidence} />
                <Row label="Recognition interval" value={`${th.recognition_interval} frame`} />
                <Row label="Cache TTL" value={`${th.cache_ttl_frames} frame`} />
                <Row label="Cache IoU" value={th.cache_iou_threshold} />
              </div>
              <div className="daily-note">
                Ambang Verified sengaja ditetapkan tinggi untuk meminimalkan
                kesalahan identifikasi, dengan konsekuensi status Unverified
                lebih sering muncul.
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

export default ModelQualityPage;