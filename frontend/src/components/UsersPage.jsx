import { useEffect, useState } from "react";
import {
  getUsers,
  createUser,
  deleteUser,
  setUserRole,
  resetUserPassword,
} from "../services/api";

const ROLES = ["user", "admin", "super_admin"];

function UsersPage({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Form tambah user
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await getUsers();
      setUsers(data.users ?? []);
      setError("");
    } catch (e) {
      setError(e.message || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const data = await createUser(newUsername, newPassword, newRole);
      setUsers(data.users ?? []);
      setNotice(`User "${newUsername.trim().toLowerCase()}" added.`);
      setNewUsername("");
      setNewPassword("");
      setNewRole("user");
    } catch (e2) {
      setError(e2.message || "Failed to add user.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(username, role) {
    setError("");
    setNotice("");
    try {
      const data = await setUserRole(username, role);
      setUsers(data.users ?? []);
      setNotice(`Role for "${username}" changed to ${role}.`);
    } catch (e) {
      setError(e.message || "Failed to change role.");
    }
  }

  async function handleResetPassword(username) {
    const pw = window.prompt(`New password for "${username}" (min 4 characters):`);
    if (pw === null) return; // dibatalkan
    setError("");
    setNotice("");
    try {
      await resetUserPassword(username, pw);
      setNotice(`Password for "${username}" updated.`);
    } catch (e) {
      setError(e.message || "Failed to reset password.");
    }
  }

  async function handleDelete(username) {
    if (!window.confirm(`Delete user "${username}"? This is permanent.`)) return;
    setError("");
    setNotice("");
    try {
      const data = await deleteUser(username);
      setUsers(data.users ?? []);
      setNotice(`User "${username}" deleted.`);
    } catch (e) {
      setError(e.message || "Failed to delete user.");
    }
  }

  return (
    <main className="users-main">
      <header className="main-header">
        <div className="header-left">
          <div className="header-camname">User Management</div>
        </div>
      </header>

      {error && <div className="users-alert error">{error}</div>}
      {notice && <div className="users-alert ok">{notice}</div>}

      <section className="panel-card">
        <h3 className="panel-title">Add User</h3>
        <form className="user-form" onSubmit={handleCreate}>
          <input
            className="login-input"
            placeholder="username"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            required
          />
          <input
            className="login-input"
            placeholder="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          <select
            className="login-input"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button className="btn-primary" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Add"}
          </button>
        </form>
      </section>

      <section className="panel-card">
        <h3 className="panel-title">User List</h3>
        {loading ? (
          <div className="empty-note">Loading...</div>
        ) : users.length === 0 ? (
          <div className="empty-note">No users yet.</div>
        ) : (
          <table className="user-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = u.username === currentUser?.username;
                return (
                  <tr key={u.id}>
                    <td>
                      {u.username}
                      {isSelf && <span className="self-tag">you</span>}
                    </td>
                    <td>
                      <select
                        className="role-select"
                        value={u.role}
                        disabled={isSelf}
                        title={isSelf ? "You can't change your own role" : ""}
                        onChange={(e) => handleRoleChange(u.username, e.target.value)}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="user-created">{u.created_at}</td>
                    <td className="user-actions">
                      <button
                        className="btn-ghost"
                        onClick={() => handleResetPassword(u.username)}
                      >
                        Reset PW
                      </button>
                      <button
                        className="btn-danger"
                        disabled={isSelf}
                        title={isSelf ? "You can't delete your own account" : "Delete user"}
                        onClick={() => handleDelete(u.username)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

export default UsersPage;