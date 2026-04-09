"""
AETHERTRADE-SWARM — Application Configuration
Pydantic-settings v2 based config with environment variable loading.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = Field(default="AETHERTRADE-SWARM API")
    app_version: str = Field(default="1.0.0")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(default="info")
    debug: bool = Field(default=False)

    # Supabase
    supabase_url: str = Field(default="https://placeholder.supabase.co")
    supabase_key: str = Field(default="placeholder_key")

    # Security
    oracle_master_key: str = Field(default="dev-master-key-change-in-production")

    # CORS — comma-separated origins
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:3001")

    # Rate limits (requests per minute)
    rate_limit_free: int = Field(default=100)
    rate_limit_pro: int = Field(default=1000)
    rate_limit_enterprise: int = Field(default=10000)

    # Redis (optional, falls back to in-memory)
    redis_url: str = Field(default="redis://localhost:6379")

    # Simulation
    simulation_seed: int = Field(default=42)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        # Accept both comma-separated string and list
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
