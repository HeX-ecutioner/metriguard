import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and/or backend/.env file.
    Provides typed, validated configuration for native Windows local execution.
    """
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'metriguard.db').as_posix()}"
    STORAGE_PATH: str = str(BACKEND_DIR / "storage")
    MAX_UPLOAD_SIZE_MB: int = 10
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    USE_MOCK_EXTRACTOR: bool = False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Parse comma-separated string if provided in .env
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def get_resolved_storage_path(self) -> Path:
        """Returns storage directory resolved relative to backend root if given as relative path."""
        path = Path(self.STORAGE_PATH)
        if not path.is_absolute():
            return (BACKEND_DIR / path).resolve()
        return path.resolve()

    def get_resolved_database_url(self) -> str:
        """
        Normalizes SQLite URLs with relative paths to absolute paths
        to avoid issues across different working directories on Windows.
        """
        url = self.DATABASE_URL
        if url.startswith("sqlite:///."):
            rel_path = url[len("sqlite:///"):]
            abs_path = (BACKEND_DIR / rel_path).resolve().as_posix()
            return f"sqlite:///{abs_path}"
        return url


settings = Settings()


def ensure_directories() -> None:
    """
    Ensures required backend directories exist:
    - backend/data/
    - backend/storage/
    - backend/storage/uploads/
    - backend/storage/reports/
    """
    data_dir = BACKEND_DIR / "data"
    storage_dir = settings.get_resolved_storage_path()
    uploads_dir = storage_dir / "uploads"
    reports_dir = storage_dir / "reports"

    for d in [data_dir, storage_dir, uploads_dir, reports_dir]:
        d.mkdir(parents=True, exist_ok=True)
