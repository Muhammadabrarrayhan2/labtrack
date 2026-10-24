from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

DEFAULT_JWT_SECRET = "local-dev-secret-change-me-before-deploying-000000"


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and .env locally)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"  # local | production
    log_level: str = "INFO"
    cors_origins: str = "*"

    # Database. Priority: DATABASE_URL > Cloud SQL socket > local SQLite
    database_url: str | None = None
    db_user: str = "labtrack"
    db_password: str = ""
    db_name: str = "labtrack"
    instance_connection_name: str | None = None  # project:region:instance

    # Auth
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    # Object storage. GCS when GCS_BUCKET is set, local folder otherwise
    gcs_bucket: str | None = None
    local_upload_dir: str = "./uploads"
    signed_url_minutes: int = 15
    max_upload_mb: int = 10

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        if self.instance_connection_name:
            # Cloud Run mounts the Cloud SQL Auth Proxy socket at /cloudsql/<connection name>
            return URL.create(
                "postgresql+psycopg",
                username=self.db_user,
                password=self.db_password,
                database=self.db_name,
                query={"host": f"/cloudsql/{self.instance_connection_name}"},
            )
        return "sqlite:///./labtrack.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
