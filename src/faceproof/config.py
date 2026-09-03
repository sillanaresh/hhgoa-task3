"""Application settings with secrets kept outside the repository."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    configured = os.environ.get("FACEPROOF_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    source_root = Path(__file__).resolve().parents[2]
    return source_root if (source_root / "pyproject.toml").is_file() else Path.cwd().resolve()


PROJECT_ROOT = _project_root()
CONTEXT_DIR = PROJECT_ROOT / ".context"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and local secret files."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", CONTEXT_DIR / "secrets.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FaceProof"
    serpapi_api_key: SecretStr | None = None
    base_rpc_url: str = "https://sepolia.base.org"
    base_chain_id: int = 84532
    base_explorer_url: str = "https://sepolia.basescan.org"
    face_match_threshold: float = Field(default=0.45, ge=-1.0, le=1.0)
    detector_score_threshold: float = Field(default=0.88, ge=0.0, le=1.0)
    max_upload_bytes: int = 10 * 1024 * 1024
    max_remote_image_bytes: int = 12 * 1024 * 1024
    max_candidates: int = Field(default=16, ge=1, le=50)
    candidate_download_concurrency: int = Field(default=4, ge=1, le=8)
    models_dir: Path = CONTEXT_DIR / "models"
    runs_dir: Path = CONTEXT_DIR / "runs"
    wallet_file: Path = CONTEXT_DIR / "base-sepolia-wallet.json"

    social_domains: tuple[str, ...] = (
        "x.com",
        "twitter.com",
        "instagram.com",
        "facebook.com",
        "threads.net",
        "linkedin.com",
        "tiktok.com",
        "youtube.com",
        "youtu.be",
        "reddit.com",
        "bsky.app",
        "pinterest.com",
    )

    @property
    def search_is_configured(self) -> bool:
        return bool(self.serpapi_api_key and self.serpapi_api_key.get_secret_value().strip())

    @property
    def wallet_exists(self) -> bool:
        return self.wallet_file.is_file()

    def ensure_runtime_dirs(self) -> None:
        for directory in {self.models_dir, self.runs_dir, self.wallet_file.parent}:
            directory.mkdir(parents=True, exist_ok=True)
            directory.chmod(0o700)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
