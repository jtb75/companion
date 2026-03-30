import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.events  # noqa: F401
from app.api.admin import router as admin_router
from app.api.admin.seed_admin import router as seed_admin_router
from app.api.caregiver import router as caregiver_router
from app.api.pipeline import router as pipeline_router
from app.api.v1 import router as v1_router
from app.api.v1.auth_check import router as auth_router
from app.api.v1.charges import router as charges_router
from app.api.v1.profile import router as profile_router
from app.branding import BRAND_LONG, BRAND_MID
from app.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=f"{BRAND_MID} API",
    description=f"{BRAND_LONG} — Independence Assistant for Adults with Developmental Disabilities",
    version="0.1.0",
    lifespan=lifespan,
)

CORS_ORIGINS = {
    "development": ["http://localhost:5173", "http://localhost:3000"],
    "staging": [
        "https://app.mydailydignity.com",
        "https://companion-staging-web-44gbcsdrnq-uc.a.run.app",
        "https://companion-staging-web-381910341082.us-central1.run.app",
        "http://localhost:5173",
    ],
    "prod": [
        "https://app.mydailydignity.com",
        "https://companion-prod-web-mtfid4sksa-uc.a.run.app",
    ],
}

_cors_origins = CORS_ORIGINS.get(settings.environment, [])
if not _cors_origins:
    logger.error(
        f"No CORS origins configured for environment '{settings.environment}'. "
        "Cross-origin requests will be blocked. "
        f"Valid environments: {list(CORS_ORIGINS.keys())}"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mount API routers
app.include_router(v1_router)
app.include_router(caregiver_router)
app.include_router(pipeline_router)
app.include_router(admin_router)
app.include_router(auth_router)
if settings.dev_auth_bypass:
    app.include_router(seed_admin_router)
    logger.warning(
        "DEV AUTH BYPASS IS ENABLED -- all endpoints accept "
        "unauthenticated requests. This must NEVER be enabled in production."
    )
app.include_router(charges_router)
app.include_router(profile_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": "0.1.0",
    }
