from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class UserCreate(ORMModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    created_at: datetime
    updated_at: datetime
