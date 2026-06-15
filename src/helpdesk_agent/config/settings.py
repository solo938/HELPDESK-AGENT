from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Renamed to avoid 'model_' protected namespace
    anthropic_api_key: str
    claude_model_name: str = "claude-3-sonnet-4-6"  # Changed from 'model_name'
    max_steps: int = 5
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 10
    circuit_breaker_threshold: int = 3
    
    # Optional: Add fallback for old name during migration
    @property
    def model_name(self) -> str:
        """Backward compatibility for 'model_name'"""
        return self.claude_model_name
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=('settings_',)  # This suppresses the warning
    )


settings = Settings()