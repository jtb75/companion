from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "COMPANION_"}

    # Database
    database_url: str = "postgresql+asyncpg://companion:companion_dev@localhost:5432/companion"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Google Cloud
    gcp_project_id: str = "companion-dev"
    pubsub_emulator_host: str | None = "localhost:8085"
    gcs_bucket_documents: str = "companion-docs-dev"

    # Firebase
    firebase_project_id: str = "companion-dev"

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "gemini"  # "gemini", "anthropic", or "openai"
    gemini_model: str = "gemini-2.5-flash"
    gemini_location: str = "us-central1"

    # Pipeline service-to-service auth
    pipeline_api_key: str = ""  # Required in production

    # Auth bypass for local development ONLY.
    # Must be explicitly set to true. Never enable in production.
    dev_auth_bypass: bool = False

    # Gmail SMTP (Google Workspace)
    gmail_smtp_user: str = "dd@mydailydignity.com"
    gmail_smtp_password: str = ""

    # App
    app_url: str = "http://localhost:5173"  # Frontend URL for email links
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"


settings = Settings()
