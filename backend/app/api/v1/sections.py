"""App API — Section aggregate views."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("/home")
async def home_section(user: User = Depends(get_current_user)):
    """Home section data — recent documents, upcoming items."""
    # TODO: aggregate home section data
    return {
        "recent_documents": [],
        "upcoming_appointments": [],
        "pending_todos": [],
        "notifications_count": 0,
    }


@router.get("/health")
async def health_section(user: User = Depends(get_current_user)):
    """My Health section data — medications, appointments."""
    # TODO: aggregate health data
    return {
        "medications": [],
        "upcoming_appointments": [],
        "recent_health_documents": [],
    }


@router.get("/bills")
async def bills_section(user: User = Depends(get_current_user)):
    """Bills section data — due bills, summary."""
    # TODO: aggregate bills data
    return {
        "due_soon": [],
        "overdue": [],
        "monthly_summary": {"total_due": 0, "total_paid": 0},
    }


@router.get("/plans")
async def plans_section(user: User = Depends(get_current_user)):
    """Plans section data — todos, upcoming plans."""
    # TODO: aggregate plans data
    return {
        "todos": [],
        "upcoming_events": [],
    }


@router.get("/today")
async def today_section(user: User = Depends(get_current_user)):
    """Cross-section priority view for today."""
    # TODO: aggregate today's priorities across sections
    return {
        "medications_due": [],
        "appointments_today": [],
        "bills_due_today": [],
        "todos_today": [],
        "priority_notifications": [],
    }
