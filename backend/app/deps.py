from fastapi import Depends, Header, HTTPException, Query

from app import auth_db


def get_current_user(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """
    Dependency FastAPI: memastikan request punya session token valid.
    Token bisa dikirim lewat:
    - Header "Authorization: Bearer <token>"  -> dipakai fetch React
    - Query "?token=<token>"                  -> dipakai <img> stream / unduhan CSV
    """
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:]
    elif token:
        raw = token

    if not raw:
        raise HTTPException(status_code=401, detail="Belum login.")

    user = auth_db.get_user_by_token(raw)
    if user is None:
        raise HTTPException(status_code=401, detail="Sesi tidak valid atau kedaluwarsa.")

    return user


def require_role(*roles):
    """Dependency tambahan: hanya role tertentu yang boleh masuk."""
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Role kamu tidak punya akses ke sini.")
        return user
    return checker
