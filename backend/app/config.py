from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    database_url: str = "sqlite:///./data/trident.db"
    prefect_api_url: str = "http://localhost:4200/api"
    log_level: str = "INFO"
    
    # CORS — comma-separated origins, or "*" for permissive dev mode
    cors_origins: str = "*"
    cors_allow_headers: str = "Content-Type,Authorization,Idempotency-Key,X-Correlation-Id"
    
    # SQLite optimizations
    sqlite_pragma_journal_mode: str = "WAL"
    sqlite_pragma_busy_timeout: int = 5000
    sqlite_pragma_synchronous: str = "NORMAL"
    sqlite_pragma_cache_size: int = -64000
    sqlite_pragma_temp_store: str = "MEMORY"


settings = Settings()
