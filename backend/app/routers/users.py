from fastapi import APIRouter, Depends, HTTPException

from app import auth_db
from app.deps import require_role
from app.models.schemas import CreateUserRequest, PasswordRequest, RoleRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def list_users_endpoint(user=Depends(require_role("super_admin"))):
    """Daftar semua user. Hanya super_admin."""
    return {"status": "ok", "users": auth_db.list_users()}


@router.post("")
def create_user_endpoint(payload: CreateUserRequest,
                         user=Depends(require_role("super_admin"))):
    """Tambah user baru."""
    username = payload.username.strip().lower()
    existing = {u["username"] for u in auth_db.list_users()}
    if username in existing:
        raise HTTPException(status_code=400, detail="Username sudah dipakai.")
    try:
        auth_db.create_user(username, payload.password, payload.role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"status": "ok", "users": auth_db.list_users()}


@router.delete("/{username}")
def delete_user_endpoint(username: str,
                         user=Depends(require_role("super_admin"))):
    """Hapus user. Aturan aman: tidak boleh menghapus akun sendiri."""
    target = username.strip().lower()
    if target == user["username"]:
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus akun sendiri.")
    try:
        auth_db.delete_user(target)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {"status": "ok", "users": auth_db.list_users()}


@router.post("/{username}/role")
def set_role_endpoint(username: str, payload: RoleRequest,
                      user=Depends(require_role("super_admin"))):
    """Ganti role user. Aturan aman: tidak boleh menurunkan/mengubah role sendiri."""
    target = username.strip().lower()
    if target == user["username"]:
        raise HTTPException(status_code=400, detail="Tidak bisa mengubah role akun sendiri.")
    try:
        auth_db.set_role(target, payload.role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"status": "ok", "users": auth_db.list_users()}


@router.post("/{username}/password")
def set_password_endpoint(username: str, payload: PasswordRequest,
                          user=Depends(require_role("super_admin"))):
    """Reset password user (boleh untuk diri sendiri)."""
    target = username.strip().lower()
    try:
        auth_db.set_password(target, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"status": "ok", "message": "Password diperbarui."}
