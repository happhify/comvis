import { useEffect, useState } from "react";
import "./App.css";

import Sidebar from "./components/Sidebar";
import VideoPanel from "./components/VideoPanel";
import DetectionStats from "./components/DetectionStats";
import TrackingHistory from "./components/TrackingHistory";
import ServerStats from "./components/ServerStats";
import DailyStats from "./components/DailyStats";
import AnalyticsPage from "./components/AnalyticsPage";
import UsersPage from "./components/UsersPage";
import ModelQualityPage from "./components/ModelQualityPage";
import LoginPage from "./components/LoginPage";

import {
  getStats,
  getServerStats,
  getDetectionHistory,
  getDailyStats,
  getControl,
  updateControl,
  getCameras,
  switchCamera,
  getMe,
  logout,
} from "./services/api";

function todayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function isStale(lastUpdate, maxAgeMs = 15000) {
  if (!lastUpdate) return true;
  // Backend menulis waktu server (UTC di dalam container Docker) tanpa
  // info timezone ("2026-08-06 02:36:33"). Tanpa akhiran "Z", browser
  // menafsirkannya sebagai waktu LOKAL browser -> di WIB (UTC+7) selisih
  // 7 jam bikin data yang sebenarnya baru selalu dianggap basi.
  const t = new Date(String(lastUpdate).replace(" ", "T") + "Z").getTime();
  if (Number.isNaN(t)) return false;
  return Date.now() - t > maxAgeMs;
}

function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [page, setPage] = useState("live");

  useEffect(() => {
    async function checkLogin() {
      try {
        setUser(await getMe());
      } catch {
        setUser(null);
      }
      setAuthChecked(true);
    }
    checkLogin();
  }, []);

  const [stats, setStats] = useState(null);
  const [serverStats, setServerStats] = useState(null);
  const [pastSessions, setPastSessions] = useState([]);
  const [daily, setDaily] = useState(null);
  const [control, setControl] = useState(null);
  const [togglingDetection, setTogglingDetection] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [cameras, setCameras] = useState(null);
  const [switchingCamera, setSwitchingCamera] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getStats();
        setStats(data);
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    }
    if (!user) return;
    load();
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [user]);

  useEffect(() => {
    async function load() {
      try {
        setServerStats(await getServerStats());
      } catch {
        setServerStats(null);
      }
    }
    if (!user || user.role === "user") return;
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [user]);

  useEffect(() => {
    async function load() {
      try {
        const data = await getDetectionHistory({
          date: todayStr(),
          status: "all",
          limit: 20,
        });
        setPastSessions(data?.data ?? []);
      } catch {
        setPastSessions([]);
      }
    }
    if (!user) return;
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [user]);

  useEffect(() => {
    async function load() {
      try {
        setDaily(await getDailyStats(14));
      } catch {
        setDaily(null);
      }
    }
    if (!user) return;
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, [user]);

  useEffect(() => {
    async function load() {
      try {
        setControl(await getControl());
      } catch {
        setControl(null);
      }
    }
    if (!user) return;
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [user]);

  useEffect(() => {
    async function load() {
      try {
        setCameras(await getCameras());
      } catch {
        setCameras(null);
      }
    }
    if (!user) return;
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [user]);

  const rawStatus = backendOnline ? stats?.camera_status ?? "WAITING" : "OFFLINE";
  const cameraStatus =
    rawStatus === "LIVE" && isStale(stats?.last_update) ? "WAITING" : rawStatus;
  const cameraName = stats?.camera_name ?? "Camera 1";
  const statusClass = String(cameraStatus).toLowerCase();
  const fpsText = Number(stats?.fps ?? 0).toFixed(1);
  const detectionOn = control?.detection_enabled ?? true;

  async function handleLogout() {
    await logout();
    setUser(null);
  }

  async function handleToggleDetection() {
    if (!control || togglingDetection) return;
    const next = !control.detection_enabled;
    setTogglingDetection(true);
    try {
      const updated = await updateControl(next);
      setControl(updated);
    } catch {
      // gagal kirim: biarkan, polling 4 detik akan menyamakan lagi
    } finally {
      setTogglingDetection(false);
    }
  }

  async function handleSelectCamera(cameraId) {
    if (!cameraId || switchingCamera || cameraId === cameras?.active_camera_id) return;
    setSwitchingCamera(true);
    try {
      await switchCamera(cameraId);
      setCameras(await getCameras());
    } catch {
      // gagal kirim: biarkan, polling 5 detik akan menyamakan lagi
    } finally {
      setSwitchingCamera(false);
    }
  }

  if (!authChecked) return null;
  if (!user) return <LoginPage onLogin={setUser} />;

  const isAdmin = user.role === "admin" || user.role === "super_admin";
  const isSuperAdmin = user.role === "super_admin";

  const appClass =
    "app" +
    (page === "analytics" ? " app-analytics" : "") +
    (page === "users" ? " app-users" : "") +
    (page === "quality" ? " app-quality" : "");

  return (
    <div className={appClass}>
      <Sidebar
        cameraStatus={cameraStatus}
        cameras={cameras}
        onSelectCamera={handleSelectCamera}
        switchingCamera={switchingCamera}
        user={user}
        onLogout={handleLogout}
        page={page}
        onNavigate={setPage}
      />

      {page === "analytics" ? (
        <AnalyticsPage stats={stats} control={control} />
      ) : page === "quality" ? (
        <ModelQualityPage />
      ) : page === "users" && isSuperAdmin ? (
        <UsersPage currentUser={user} />
      ) : (
        <>
          <main className="main">
            <header className="main-header">
              <div className="header-left">
                <span className={`live-badge ${statusClass}`}>
                  <span className="live-dot"></span>
                  {cameraStatus}
                </span>
                <span className="header-sep">&middot;</span>
                <div className="header-camname">{cameraName}</div>
              </div>
              <div className="header-chips">
                {isAdmin && (
                  <button
                    className={`detect-toggle ${detectionOn ? "on" : "off"}`}
                    onClick={handleToggleDetection}
                    disabled={togglingDetection}
                    title="Click to turn detection on / off"
                  >
                    <span className="detect-dot"></span>
                    Detection {detectionOn ? "ON" : "OFF"}
                  </button>
                )}
                <div className="chip">
                  <span className="chip-label">People in frame</span>
                  <span className="chip-value">{stats?.people_in_frame ?? 0}</span>
                </div>
                <div className="chip">
                  <span className="chip-label">Total detections</span>
                  <span className="chip-value">
                    {(stats?.total_detections ?? 0).toLocaleString("en-US")}
                  </span>
                </div>
                <div className="chip">
                  <span className="chip-label">FPS</span>
                  <span className="chip-value">{fpsText}</span>
                </div>
              </div>
            </header>
            <VideoPanel cameraStatus={cameraStatus} backendOnline={backendOnline} />
          </main>
          <aside className="rightpanel">
            <DetectionStats stats={stats} />
            <TrackingHistory
              activePersons={stats?.active_persons}
              pastSessions={pastSessions}
            />
            <DailyStats daily={daily} />
            {isAdmin && <ServerStats data={serverStats} />}
          </aside>
        </>
      )}
    </div>
  );
}

export default App;