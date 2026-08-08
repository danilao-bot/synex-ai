"""Configuration settings and environment validation for Synex backend."""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Synex AI Data Engineering Agent"
    
    # DataHub URLs and Tokens
    DATAHUB_GMS_URL: str = "http://localhost:8080"
    DATAHUB_MCP_URL: str = ""
    DATAHUB_PAT: str = ""
    DATAHUB_SERVICE_ACCOUNT_TOKEN: str = ""
    # TODO(Phase write-back hardening): when False, still allow approved emits but log that gate is open for demo.
    # Approval endpoint remains the human gate; this flag can force-disable mutations in locked environments.
    DATAHUB_MCP_MUTATIONS_ENABLED: bool = True

    # LLM Settings
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-4o"
    LLM_PROVIDER: str = "openrouter"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_FAST_MODEL: str = "openai/gpt-4o-mini"
    LLM_REASONING_MODEL: str = "openai/gpt-4o"
    LLM_FALLBACK_ORDER: str = "openrouter,openai,anthropic,groq,gemini"
    LLM_MAX_RETRIES: int = 2
    LLM_TIMEOUT_SECONDS: float = 60.0
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ENABLE_LLM_CRITIQUE: bool = True

    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", repr=False)

    # Security & CORS
    FRONTEND_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Security Architecture Controls
    SYNEX_API_KEY: str = "synex_developer_secret_token"
    JWT_SECRET: str = "synex_jwt_secret_dev_key_change_me_in_prod"
    # A valid default Fernet key for encrypting secrets (can be overridden in production)
    ENCRYPTION_KEY: str = "L8j3H_b2e1t_Z6w5q4_o3n2_s1a_b9c8d7e6f5g4h3i="
    RATE_LIMIT_RPM: int = 60
    DEV_MODE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

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
