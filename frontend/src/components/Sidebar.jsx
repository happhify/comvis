import { useState } from "react";

function Sidebar({
  cameraStatus,
  cameras,
  onSelectCamera,
  switchingCamera,
  user,
  onLogout,
  page,
  onNavigate,
}) {
  const statusClass = String(cameraStatus || "offline").toLowerCase();
  const [search, setSearch] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);

  const cameraList = cameras?.cameras ?? [];
  const activeCameraId = cameras?.active_camera_id;
  const activeCamera = cameraList.find((cam) => cam.id === activeCameraId);

  const filteredCameras = search.trim()
    ? cameraList.filter((cam) =>
        String(cam.name || cam.id)
          .toLowerCase()
          .includes(search.trim().toLowerCase())
      )
    : cameraList;

  function handlePick(cameraId) {
    onSelectCamera?.(cameraId);
    setPickerOpen(false);
    setSearch("");
  }

  const menu = [
    { key: "live", icon: "▣", label: "Live Monitor" },
    { key: "analytics", icon: "▤", label: "Analytics" },
  ];
  // Menu User Management hanya muncul untuk super_admin
  if (user?.role === "super_admin") {
    menu.push({ key: "users", icon: "◆", label: "Users" });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">CV</div>
        <div>
          <div className="brand-title">ComVis Monitor</div>
          <div className="brand-sub">PUSDATIN &middot; Employee Detection</div>
        </div>
      </div>

      <div className="sidebar-section-label">Menu</div>
      <nav className="sidebar-nav">
        {menu.map((m) => (
          <button
            key={m.key}
            className={`nav-item ${page === m.key ? "active" : ""}`}
            onClick={() => onNavigate?.(m.key)}
          >
            <span className="nav-ico">{m.icon}</span>
            <span>{m.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-section-label">Camera</div>

      <div className="camera-current">
        <div className="camera-item active no-hover">
          <span className={`status-dot ${statusClass}`}></span>
          <div className="camera-info">
            <div className="camera-name">
              {activeCamera?.name ?? "No camera selected"}
            </div>
            <div className="camera-status">{cameraStatus || "OFFLINE"}</div>
          </div>
        </div>

        {cameraList.length > 1 && (
          <button
            type="button"
            className="camera-switch-btn"
            onClick={() => setPickerOpen((v) => !v)}
            disabled={switchingCamera}
          >
            {pickerOpen ? "Cancel" : `Switch camera (${cameraList.length})`}
          </button>
        )}
      </div>

      {pickerOpen && (
        <div className="camera-picker">
          {cameraList.length > 6 && (
            <input
              className="camera-search"
              type="text"
              placeholder="Search camera..."
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          )}

          <div className="camera-list">
            {filteredCameras.length === 0 ? (
              <div className="empty-note">No camera matches "{search}".</div>
            ) : (
              filteredCameras.map((cam) => {
                const isActive = cam.id === activeCameraId;

                return (
                  <button
                    key={cam.id}
                    type="button"
                    className={`camera-item ${isActive ? "active" : ""}`}
                    onClick={() => handlePick(cam.id)}
                    disabled={switchingCamera}
                    title={cam.name}
                  >
                    <span
                      className={`status-dot ${isActive ? statusClass : ""}`}
                    ></span>
                    <div className="camera-info">
                      <div className="camera-name">{cam.name || cam.id}</div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}

      {user && (
        <div className="sidebar-user">
          <div className="user-avatar">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <div className="user-info">
            <div className="user-name">{user.username}</div>
            <div className={`user-role role-${user.role}`}>
              {user.role.replace("_", " ")}
            </div>
          </div>
          <button className="logout-btn" onClick={onLogout} title="Log out">
            Log out
          </button>
        </div>
      )}

      <div className="sidebar-footer">
        Internship prototype &middot; RTSP CCTV
        <br />
        YOLO + Classifier
      </div>
    </aside>
  );
}

export default Sidebar;