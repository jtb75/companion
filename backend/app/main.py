from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Companion API",
    description="Independence Assistant for Adults with Developmental Disabilities",
    version="0.1.0",
    lifespan=lifespan,
)

CORS_ORIGINS = {
    "development": ["http://localhost:5173", "http://localhost:3000"],
    "staging": [
        "https://companion-staging-web-44gbcsdrnq-uc.a.run.app",
    ],
    "prod": [
        "https://companion-prod-web-mtfid4sksa-uc.a.run.app",
    ],
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS.get(settings.environment, []),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}
