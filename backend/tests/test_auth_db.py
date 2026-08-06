import pytest

from app import auth_db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Tiap test pakai file SQLite sendiri, tidak nyentuh data/comvis_auth.db asli."""
    monkeypatch.setattr(auth_db, "DB_PATH", tmp_path / "test_auth.db")
    auth_db.init_db()


# ============================================================
# init_db / seeding
# ============================================================

def test_init_db_seeds_three_default_users():
    users = auth_db.list_users()
    usernames = {u["username"] for u in users}
    assert usernames == {"superadmin", "admin", "user"}


def test_default_users_have_expected_roles():
    users = {u["username"]: u["role"] for u in auth_db.list_users()}
    assert users["superadmin"] == "super_admin"
    assert users["admin"] == "admin"
    assert users["user"] == "user"


# ============================================================
# create_user
# ============================================================

def test_create_user_success():
    auth_db.create_user("budi", "password123", "user")
    usernames = {u["username"] for u in auth_db.list_users()}
    assert "budi" in usernames


def test_create_user_rejects_unknown_role():
    with pytest.raises(ValueError):
        auth_db.create_user("budi", "password123", "superuser")


def test_create_user_rejects_short_password():
    with pytest.raises(ValueError):
        auth_db.create_user("budi", "abc", "user")


def test_create_user_rejects_empty_username():
    with pytest.raises(ValueError):
        auth_db.create_user("", "password123", "user")


def test_create_user_normalizes_username_case():
    auth_db.create_user("BuDi", "password123", "user")
    usernames = {u["username"] for u in auth_db.list_users()}
    assert "budi" in usernames
    assert "BuDi" not in usernames


# ============================================================
# verify_login
# ============================================================

def test_verify_login_success():
    auth_db.create_user("budi", "password123", "user")
    user = auth_db.verify_login("budi", "password123")
    assert user is not None
    assert user["username"] == "budi"
    assert user["role"] == "user"


def test_verify_login_wrong_password_fails():
    auth_db.create_user("budi", "password123", "user")
    assert auth_db.verify_login("budi", "wrongpassword") is None


def test_verify_login_unknown_user_fails():
    assert auth_db.verify_login("nobody", "whatever123") is None


def test_verify_login_case_insensitive_username():
    auth_db.create_user("budi", "password123", "user")
    user = auth_db.verify_login("BUDI", "password123")
    assert user is not None


# ============================================================
# set_password / set_role / delete_user
# ============================================================

def test_set_password_changes_login():
    auth_db.create_user("budi", "password123", "user")
    auth_db.set_password("budi", "newpassword456")

    assert auth_db.verify_login("budi", "password123") is None
    assert auth_db.verify_login("budi", "newpassword456") is not None


def test_set_password_unknown_user_raises():
    with pytest.raises(ValueError):
        auth_db.set_password("nobody", "newpassword456")


def test_set_role_updates_role():
    auth_db.create_user("budi", "password123", "user")
    auth_db.set_role("budi", "admin")
    users = {u["username"]: u["role"] for u in auth_db.list_users()}
    assert users["budi"] == "admin"


def test_set_role_rejects_unknown_role():
    auth_db.create_user("budi", "password123", "user")
    with pytest.raises(ValueError):
        auth_db.set_role("budi", "superuser")


def test_delete_user_removes_user():
    auth_db.create_user("budi", "password123", "user")
    auth_db.delete_user("budi")
    usernames = {u["username"] for u in auth_db.list_users()}
    assert "budi" not in usernames


def test_delete_unknown_user_raises():
    with pytest.raises(ValueError):
        auth_db.delete_user("nobody")


# ============================================================
# Session handling
# ============================================================

def test_create_and_lookup_session():
    auth_db.create_user("budi", "password123", "user")
    user = auth_db.verify_login("budi", "password123")
    token = auth_db.create_session(user["id"])

    fetched = auth_db.get_user_by_token(token)
    assert fetched is not None
    assert fetched["username"] == "budi"


def test_get_user_by_invalid_token_returns_none():
    assert auth_db.get_user_by_token("not-a-real-token") is None


def test_get_user_by_empty_token_returns_none():
    assert auth_db.get_user_by_token("") is None
    assert auth_db.get_user_by_token(None) is None


def test_delete_session_invalidates_token():
    auth_db.create_user("budi", "password123", "user")
    user = auth_db.verify_login("budi", "password123")
    token = auth_db.create_session(user["id"])

    auth_db.delete_session(token)

    assert auth_db.get_user_by_token(token) is None


def test_deleting_user_also_deletes_their_sessions():
    auth_db.create_user("budi", "password123", "user")
    user = auth_db.verify_login("budi", "password123")
    token = auth_db.create_session(user["id"])

    auth_db.delete_user("budi")

    assert auth_db.get_user_by_token(token) is None
