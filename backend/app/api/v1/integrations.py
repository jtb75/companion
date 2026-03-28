"""App API — Integration routes."""

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post("/gmail/connect", status_code=status.HTTP_201_CREATED)
async def connect_gmail(user: User = Depends(get_current_user)):
    """Initiate Gmail OAuth connection."""
    # TODO: generate OAuth URL and return for redirect
    return {
        "provider": "gmail",
        "oauth_url": "https://accounts.google.com/o/oauth2/auth?placeholder=true",
        "status": "pending",
    }


@router.delete("/gmail", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_gmail(user: User = Depends(get_current_user)):
    """Disconnect Gmail integration."""
    # TODO: revoke OAuth tokens and remove integration
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
    # TODO: check actual connection status for each provider
    return {
        "gmail": {"connected": False, "last_sync": None},
        "plaid": {"connected": False, "last_sync": None},
    }
