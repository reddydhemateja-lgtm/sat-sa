from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import RoleEnum


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: RoleEnum = RoleEnum.ANALYST


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: RoleEnum | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime