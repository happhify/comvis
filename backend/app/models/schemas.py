from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class ControlRequest(BaseModel):
    # Keduanya opsional: dashboard bisa kirim salah satu saja
    # (mis. cuma ganti kamera tanpa mengubah saklar deteksi).
    detection_enabled: bool | None = None
    camera_id: str | None = None


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str


class RoleRequest(BaseModel):
    role: str


class PasswordRequest(BaseModel):
    password: str
