"""App API — Section aggregate views."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.db import get_db
from app.services import section_service

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("/home")
async def home_section(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Home section data — recent documents, upcoming items."""
    return await section_service.get_home_section(db, user.id)


@router.get("/health")
async def health_section(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """My Health section data — medications, appointments."""
    return await section_service.get_health_section(db, user.id)


@router.get("/bills")
async def bills_section(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Bills section data — due bills, summary."""
    return await section_service.get_bills_section(db, user.id)


@router.get("/plans")
async def plans_section(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Plans section data — todos, upcoming plans."""
    return await section_service.get_plans_section(db, user.id)


@router.get("/today")
async def today_section(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Cross-section priority view for today."""
    return await section_service.get_today_section(db, user.id)
