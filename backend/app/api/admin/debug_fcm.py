"""Admin API — FCM debug endpoint."""

import json
import os

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin_role
from app.db import get_db
from app.models.device_token import DeviceToken

router = APIRouter(
    prefix="/admin/debug",
    tags=["Admin - Debug"],
)

_editor = require_admin_role("editor")


@router.get("/test-fcm")
async def test_fcm(
    device_token: str = "fake_test_token_for_debug",
    user_email: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Test FCM connectivity from inside the container."""
    results = {}

    # If user_email provided, look up their device token
    if user_email and device_token == "fake_test_token_for_debug":
        from app.models.user import User

        user_result = await db.execute(
            select(User).where(User.email == user_email)
        )
        user = user_result.scalar_one_or_none()
        if user:
            token_result = await db.execute(
                select(DeviceToken).where(
                    DeviceToken.user_id == user.id,
                    DeviceToken.is_active.is_(True),
                )
            )
            dt = token_result.scalar_one_or_none()
            if dt:
                device_token = dt.fcm_token
                results["db_token_len"] = len(device_token)
                results["db_token_prefix"] = device_token[:30]
                results["db_user_id"] = str(user.id)
            else:
                results["db_error"] = "no active token"
        else:
            results["db_error"] = "user not found"

    # 1. Check env vars
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    results["cred_path"] = cred_path
    results["cred_exists"] = (
        os.path.exists(cred_path) if cred_path else False
    )
    results["project_id"] = os.environ.get(
        "COMPANION_FIREBASE_PROJECT_ID"
    )

    # 2. Read and verify key file
    sa_info = None
    if results["cred_exists"]:
        with open(cred_path) as f:
            sa_info = json.load(f)
        results["sa_email"] = sa_info.get("client_email")
        results["sa_project"] = sa_info.get("project_id")
        results["sa_type"] = sa_info.get("type")
        results["key_size"] = os.path.getsize(cred_path)

    # 3. Try to get OAuth token
    token = None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=[
                "https://www.googleapis.com/auth/firebase.messaging",
            ],
        )
        credentials.refresh(Request())
        token = credentials.token
        results["token_len"] = len(token)
        results["token_valid"] = credentials.valid
        results["token_prefix"] = token[:30] + "..."
        results["token_expiry"] = str(credentials.expiry)
    except Exception as e:
        results["token_error"] = str(e)

    if not token:
        return results

    # 4. Make a dry-run FCM call with a fake token
    project_id = results["project_id"] or sa_info.get(
        "project_id"
    )
    url = (
        f"https://fcm.googleapis.com/v1/projects/{project_id}"
        f"/messages:send"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "message": {
            "token": device_token,
            "notification": {
                "title": "Debug Test",
                "body": "This is a test",
            },
        }
    }

    results["fcm_url"] = url
    results["auth_header_len"] = len(headers["Authorization"])

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=headers,
                content=json.dumps(payload),
            )
        results["fcm_status"] = resp.status_code
        results["fcm_response"] = resp.text[:1000]
        results["fcm_headers"] = dict(resp.headers)
    except Exception as e:
        results["fcm_error"] = str(e)

    # 5. Also try with requests library (sync)
    try:
        import requests

        resp2 = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10,
        )
        results["requests_status"] = resp2.status_code
        results["requests_response"] = resp2.text[:1000]
    except Exception as e:
        results["requests_error"] = str(e)

    return results
