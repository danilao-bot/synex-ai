from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Synex AI Data Engineering Agent"
    DATAHUB_GMS_URL: str = "http://localhost:8080"
    DATAHUB_PAT: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", repr=False)
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
