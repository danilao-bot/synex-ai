"""Configuration settings and environment validation for Synex backend."""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Synex AI Data Engineering Agent"
    
    # DataHub URLs and Tokens
    DATAHUB_GMS_URL: str = "http://localhost:8080"
    DATAHUB_MCP_URL: str = ""
    DATAHUB_PAT: str = ""
    DATAHUB_SERVICE_ACCOUNT_TOKEN: str = ""
    DATAHUB_MCP_MUTATIONS_ENABLED: bool = False

    # LLM Settings
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-4o"
    LLM_PROVIDER: str = "openrouter"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", repr=False)

    # Security & CORS
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def frontend_origins_list(self) -> List[str]:
        """Return CORS allowed origins as a parsed list."""
        if not self.FRONTEND_ORIGINS:
            return ["http://localhost:3000"]
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    def get_datahub_auth_token(self) -> str:
        """Return Service Account Token if available, falling back to PAT."""
        return self.DATAHUB_SERVICE_ACCOUNT_TOKEN or self.DATAHUB_PAT or ""

    def validate_runtime_config(self) -> dict[str, str]:
        """Validate configuration health and detect cloud vs localhost mismatches."""
        issues: dict[str, str] = {}
        
        # Check LLM API Key
        if not self.LLM_API_KEY:
            issues["LLM_API_KEY"] = "LLM_API_KEY is not set. Code synthesis will fail without an API key."

        # Check DataHub GMS
        if not self.DATAHUB_GMS_URL:
            issues["DATAHUB_GMS_URL"] = "DATAHUB_GMS_URL is missing. DataHub context discovery is disabled."

        # Detect cloud environment using localhost DataHub URL
        is_cloud_env = os.getenv("RENDER") or os.getenv("VERCEL") or os.getenv("HEROKU")
        if is_cloud_env and ("localhost" in self.DATAHUB_GMS_URL or "127.0.0.1" in self.DATAHUB_GMS_URL):
            issues["DATAHUB_CLOUD_MISMATCH"] = (
                f"Cloud deployment detected but DATAHUB_GMS_URL is set to '{self.DATAHUB_GMS_URL}'. "
                "Cloud backends cannot reach local host URLs; configure a publicly accessible DataHub endpoint."
            )

        return issues


settings = Settings()
