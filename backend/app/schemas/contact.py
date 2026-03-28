from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AccessTier, RelationshipType


class ContactCreate(BaseModel):
    contact_name: str = Field(description="Full name of the trusted contact")
    contact_phone: str | None = Field(default=None, description="Phone number")
    contact_email: str | None = Field(default=None, description="Email address")
    relationship_type: RelationshipType = Field(description="Relationship to the user")


class ContactUpdate(BaseModel):
    contact_name: str | None = Field(default=None, description="Full name")
    contact_phone: str | None = Field(default=None, description="Phone number")
    contact_email: str | None = Field(default=None, description="Email address")
    access_tier: AccessTier | None = Field(default=None, description="Access tier level")
    tier_3_scope: dict | None = Field(default=None, description="Tier-3 access scope configuration")
    is_active: bool | None = Field(default=None, description="Whether the contact is active")


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    contact_name: str
    contact_phone: str | None = None
    contact_email: str | None = None
    relationship_type: RelationshipType
    access_tier: AccessTier
    tier_3_scope: dict | None = None
    is_active: bool
    added_at: datetime
    last_viewed_at: datetime | None = None
