// Dev (vite dev server): frontend/.env.development mengisi VITE_API_BASE_URL
// dengan http://localhost:8000 supaya fetch tetap ke backend lokal.
// Docker (nginx): variabel ini tidak diisi -> BASE_URL kosong -> fetch relatif
// ("/api/...") yang di-proxy oleh nginx ke service backend.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const TOKEN_KEY = "comvis_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function fetchJson(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    const hadToken = Boolean(token);
    clearToken();
    if (hadToken) {
      window.location.reload();
    }
    throw new Error("Belum login atau sesi berakhir.");
  }

  if (!res.ok) {
    // Ambil pesan "detail" dari backend kalau ada, supaya error lebih jelas
    // (mis. "Username sudah dipakai." / "Tidak bisa menghapus akun sendiri.")
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch {
      // body bukan JSON: pakai pesan default
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function login(username, password) {
  const res = await fetch(`${BASE_URL}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (res.status === 401) {
    throw new Error("Username atau password salah.");
  }
  if (!res.ok) {
    throw new Error(`Login gagal (HTTP ${res.status}).`);
  }
  const data = await res.json();
  setToken(data.token);
  return data.user;
}

export async function logout() {
  try {
    await fetchJson("/api/logout", { method: "POST" });
  } catch {
    // abaikan
  }
  clearToken();
}

export function getMe() {
  return fetchJson("/api/me");
}

export function getVideoFeedUrl() {
  return `${BASE_URL}/api/stream?token=${getToken() ?? ""}`;
}

export function getStats() {
  return fetchJson("/api/stats");
}
export function getServerStats() {
  return fetchJson("/api/server-stats");
}
export function getDailyStats(days = 14) {
  return fetchJson(`/api/daily-stats?days=${days}`);
}
export function getHourlyStats(date) {
  const q = date ? `?date=${date}` : "";
  return fetchJson(`/api/hourly-stats${q}`);
}
export function getControl() {
  return fetchJson("/api/control");
}
export function updateControl(enabled) {
  return fetchJson("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ detection_enabled: enabled }),
  });
}

// (Kamera) Daftar kamera yang bisa dipilih + pindah kamera aktif
export function getCameras() {
  return fetchJson("/api/cameras");
}
export function switchCamera(cameraId) {
  return fetchJson("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ camera_id: cameraId }),
  });
}

// ---------- (Tahap A) Kelola User — khusus super_admin ----------
export function getUsers() {
  return fetchJson("/api/users");
}
export function createUser(username, password, role) {
  return fetchJson("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
}
export function deleteUser(username) {
  return fetchJson(`/api/users/${encodeURIComponent(username)}`, {
    method: "DELETE",
  });
}
export function setUserRole(username, role) {
  return fetchJson(`/api/users/${encodeURIComponent(username)}/role`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
}
export function resetUserPassword(username, password) {
  return fetchJson(`/api/users/${encodeURIComponent(username)}/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
}

// Status kehadiran hari ini (hadir sejak jam berapa / belum datang)
export function getAttendanceToday() {
  return fetchJson("/api/attendance-today");
}

// (Riwayat) Daftar kejadian deteksi dengan filter
export function getDetectionHistory({ date, status, limit, offset }) {
  const p = new URLSearchParams();
  if (date) p.set("date", date);
  if (status) p.set("status", status);
  if (limit) p.set("limit", limit);
  if (offset != null) p.set("offset", offset);
  return fetchJson(`/api/detection-history?${p.toString()}`);
}

// (Riwayat) URL ekspor CSV (token via query karena unduhan tak bisa kirim header)
export function getHistoryExportUrl({ date, status }) {
  const p = new URLSearchParams();
  if (date) p.set("date", date);
  if (status) p.set("status", status);
  p.set("token", getToken() ?? "");
  return `${BASE_URL}/api/detection-history/export?${p.toString()}`;
}