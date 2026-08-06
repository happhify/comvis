// ============================================================
// components/VideoPanel.jsx
// Menampilkan live stream MJPEG dari FastAPI (/api/stream).
// Frame yang tampil SUDAH berisi bounding box + label,
// karena anotasi dilakukan di Python (main.py), bukan di React.
// ============================================================

import { useEffect, useState } from "react";
import { getVideoFeedUrl } from "../services/api";

function VideoPanel({ cameraStatus, backendOnline }) {
  const [streamError, setStreamError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  // Kalau stream error, coba sambung ulang tiap 8 detik secara otomatis
  useEffect(() => {
    if (!streamError) return;
    const id = setInterval(() => {
      setStreamError(false);
      setRetryKey((k) => k + 1);
    }, 8000);
    return () => clearInterval(id);
  }, [streamError]);

  let placeholderText = "Connecting to stream...";
  if (!backendOnline) {
    placeholderText =
      "Backend offline. Run: uvicorn backend.app:app --port 8000";
  } else if (cameraStatus === "WAITING") {
    placeholderText =
      "Backend online, waiting for frames from main.py. Run: python main.py";
  } else if (streamError) {
    placeholderText = "Stream disconnected. Reconnecting...";
  }

  const showPlaceholder =
    streamError || !backendOnline || cameraStatus === "WAITING";

  return (
    <div className="video-panel">
      <div className="video-frame">
        {!showPlaceholder && (
          <img
            key={retryKey}
            className="video-img"
            src={`${getVideoFeedUrl()}&r=${retryKey}`}
            alt="Live CCTV stream"
            onError={() => setStreamError(true)}
          />
        )}

        {showPlaceholder && (
          <div className="video-placeholder">
            <div className="ph-icon">||</div>
            <div>{placeholderText}</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoPanel;