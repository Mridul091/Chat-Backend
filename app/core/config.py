from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ENVIRONMENT: str = "development"
    # Comma-separated IPs/CIDRs (or "*") allowed to set X-Forwarded-For.
    # Behind nginx in Docker this must include nginx, or every client shares
    # nginx's IP for rate limiting.
    TRUSTED_PROXIES: str = "127.0.0.1"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
