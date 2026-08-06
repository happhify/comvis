from fastapi import APIRouter, Depends, Header, HTTPException

from app import auth_db
from app.deps import get_current_user
from app.models.schemas import LoginRequest

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest):
    user = auth_db.verify_login(payload.username, payload.password)

    if user is None:
        raise HTTPException(status_code=401, detail="Username atau password salah.")

    token = auth_db.create_session(user["id"])

    return {
        "status": "ok",
        "token": token,
        "user": {"username": user["username"], "role": user["role"]},
    }


@router.post("/logout")
def logout(user=Depends(get_current_user),
           authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        auth_db.delete_session(authorization[7:])
    return {"status": "ok", "message": "Berhasil logout."}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"username": user["username"], "role": user["role"]}
