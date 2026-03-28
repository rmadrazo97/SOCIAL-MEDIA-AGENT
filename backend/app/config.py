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

    # Instagram Web Session (browser cookie-based scraping)
    INSTAGRAM_SESSION_ID: str = ""
    INSTAGRAM_CSRF_TOKEN: str = ""
    INSTAGRAM_SYNC_DELAY_MIN: int = 2
    INSTAGRAM_SYNC_DELAY_MAX: int = 5
    INSTAGRAM_SYNC_BATCH_SIZE: int = 50
    INSTAGRAM_MEDIA_DIR: str = "/data/media"

    class Config:
        env_file = ".env"


settings = Settings()
