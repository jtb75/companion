"""App API — Integration routes."""

from fastapi import APIRouter, Depends, Request, status

from app.auth.dependencies import User, get_current_user
from app.integrations.gmail import (
    disconnect as gmail_disconnect,
)
from app.integrations.gmail import (
    initiate_oauth,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post("/gmail/connect", status_code=status.HTTP_201_CREATED)
async def connect_gmail(
    request: Request, user: User = Depends(get_current_user)
):
    """Initiate Gmail OAuth connection."""
    redirect_uri = str(request.url_for("connect_gmail")).replace(
        "/connect", "/callback"
    )
    oauth_url = await initiate_oauth(
        user_id=str(user.id), redirect_uri=redirect_uri
    )
    return {
        "provider": "gmail",
        "oauth_url": oauth_url,
        "status": "pending",
    }


@router.delete("/gmail", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_gmail(user: User = Depends(get_current_user)):
    """Disconnect Gmail integration."""
    await gmail_disconnect(user_id=str(user.id))
    return None


@router.post("/plaid/connect", status_code=status.HTTP_201_CREATED)
async def connect_plaid(user: User = Depends(get_current_user)):
    """Initiate Plaid connection."""
    # TODO: create Plaid link token
    return {
        "provider": "plaid",
        "link_token": "placeholder-link-token",
        "status": "pending",
    }


@router.delete("/plaid", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_plaid(user: User = Depends(get_current_user)):
    """Disconnect Plaid integration."""
    # TODO: revoke Plaid access and remove integration
    return None


@router.get("/status")
async def integration_status(user: User = Depends(get_current_user)):
    """Get status of all integrations."""
    # TODO: look up actual Gmail connection state from DB/cache
    gmail_connected = False
    gmail_email = None

    return {
        "gmail": {
            "connected": gmail_connected,
            "email": gmail_email,
            "last_sync": None,
        },
        "plaid": {"connected": False, "last_sync": None},
    }
