from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BACKEND_DIR.parent

# Keep compatibility with the original root .env while also allowing a
# backend-local file in the split project.
load_dotenv(REPOSITORY_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=False)


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _as_bool(value: str, *, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_version: str
    api_prefix: str
    backend_dir: Path
    data_dir: Path
    database_url: str
    sql_echo: bool
    cors_origins: tuple[str, ...]
    deepseek_model: str
    embedding_model: str
    chroma_collection: str
    chroma_directory: Path
    handbook_path: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data_dir = Path(os.getenv("CHAT_HUB_DATA_DIR", BACKEND_DIR / "data")).resolve()
    database_path = data_dir / "chat.db"
    database_url = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    return Settings(
        app_name=os.getenv("APP_NAME", "Chat Hub API"),
        app_version=os.getenv("APP_VERSION", "0.2.0"),
        api_prefix=os.getenv("API_PREFIX", "/api/v1"),
        backend_dir=BACKEND_DIR,
        data_dir=data_dir,
        database_url=database_url,
        sql_echo=_as_bool(os.getenv("SQL_ECHO", "false")),
        cors_origins=_split_csv(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            )
        ),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3"),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "handbook"),
        chroma_directory=Path(
            os.getenv("CHROMA_DIRECTORY", data_dir / "chroma_db")
        ).resolve(),
        handbook_path=Path(
            os.getenv("HANDBOOK_PATH", BACKEND_DIR / "app" / "resources" / "handbook.md")
        ).resolve(),
    )


settings = get_settings()
