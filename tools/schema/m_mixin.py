from typing import Any, Dict, Optional
from sqlmodel import Column, Column, SQLModel, Field
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid

class BaseMixin(SQLModel):
    tenant_id: uuid.UUID = Field(index=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default="create_user")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(default="update_user")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_by: Optional[str] = Field(default="delete_user")

    version: int = Field(default=1)  # optimistic locking
    status: str = Field(default="active")

    description: Optional[str] = Field(default="Description")
    is_deleted: bool = Field(default=False)  # soft delete flag


class ActiveMixin(SQLModel):
    is_active: bool = Field(default=True)
    is_archived: bool = Field(default=False)

class VerificationMixin(SQLModel):
    is_verified: bool = Field(default=False)
    is_verified_email: bool = Field(default=False)
    is_verified_phone: bool = Field(default=False)

class PublishingMixin(SQLModel):
    is_published: bool = Field(default=False)
    is_featured: bool = Field(default=False)

class ApprovalMixin(SQLModel):
    is_approved: bool = Field(default=False)
    is_locked: bool = Field(default=False)
    is_reviewed: bool = Field(default=False)
    is_flagged: bool = Field(default=False)


class ReadMixin(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default="create_user")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(default="update_user")

    status: str = Field(default="active")
    status2: str = Field(default="second status")
