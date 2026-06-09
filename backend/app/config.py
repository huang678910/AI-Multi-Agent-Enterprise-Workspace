"""
应用配置 — 通过 pydantic-settings 从环境变量/.env 加载
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 从 backend/app/config.py 向上找到项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # --- 应用 ---
    APP_NAME: str = "AI Multi-Agent Enterprise Workspace"
    DEBUG: bool = True
    UPLOAD_DIR: str = str(_PROJECT_ROOT / "backend" / "uploads")

    # --- 数据库 ---
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ai_workspace"
    DATABASE_URL: str = ""

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = ""
    REDIS_ENABLED: bool = True

    # --- WebSocket ---
    WS_HEARTBEAT_INTERVAL: int = 30

    # --- 速率限制 ---
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- DeepSeek API ---
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    # --- Tavily Search API ---
    TAVILY_API_KEY: str = ""

    # --- Embedding ---
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIM: int = 512
    HF_ENDPOINT: str = "https://hf-mirror.com"

    # --- JWT ---
    SECRET_KEY: str = "change-me-to-a-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ALGORITHM: str = "HS256"

    # --- Neo4j Knowledge Graph ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    if not s.DEEPSEEK_API_KEY:
        import logging
        logging.getLogger(__name__).warning(
            f"DEEPSEEK_API_KEY is empty! Chat will fail. "
            f"Set it in {_ENV_FILE} or as environment variable."
        )
    return s
