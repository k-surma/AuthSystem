from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    face_id: str
    is_active: bool = True


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    face_id: str
    is_active: bool

    class Config:
        from_attributes = True


class BadgeCreate(BaseModel):
    qr_code: str
    valid_until: date
    user_id: int


class BadgeResponse(BaseModel):
    id: int
    qr_code: str
    valid_until: date
    user_id: int

    class Config:
        from_attributes = True


class VerificationRequest(BaseModel):
    qr_code: str
    # image will be sent as form data


class AccessLogResponse(BaseModel):
    id: int
    timestamp: datetime
    result: str
    match_score: Optional[float]
    badge_id: Optional[int]
    user_id: Optional[int]
    image_path: Optional[str]

    class Config:
        from_attributes = True


class VerificationResponse(BaseModel):
    success: bool
    message: str
    result: str  # ACCEPT, REJECT, SUSPICIOUS
    match_score: Optional[float] = None
    user_id: Optional[int] = None
    log_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


