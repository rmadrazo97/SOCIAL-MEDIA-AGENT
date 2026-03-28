from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://smadmin:sm_agent_dev_2026@db:5432/social_media_agent"
    REDIS_URL: str = "redis://redis:6379/0"
    APP_PASSWORD: str = "admin123"
    MOONSHOT_API_KEY: str = ""
    INSTAGRAM_USERNAME: str = ""
    INSTAGRAM_PASSWORD: str = ""
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_PROXY: str = ""
    ENCRYPTION_KEY: str = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

    class Config:
        env_file = ".env"


settings = Settings()
