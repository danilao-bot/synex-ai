import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Synex AI Data Engineering Agent"
    DATAHUB_GMS_URL: str = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
    DATAHUB_PAT: str = os.getenv("DATAHUB_PAT", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
