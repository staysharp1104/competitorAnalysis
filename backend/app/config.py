from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    database_url: str = "sqlite+aiosqlite:///./data/competitor_analysis.db"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    upload_dir: str = "./uploads"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
if settings.is_sqlite:
    os.makedirs(os.path.dirname(settings.database_url.replace("sqlite+aiosqlite:///", "")), exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)
