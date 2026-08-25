from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    # App security
    APP_API_KEY: str = Field(..., description="Internal API key for authentication")
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # Rate limiting
    DEFAULT_RATE_LIMIT: str = "30/minute"
    EXPENSIVE_ROUTE_RATE_LIMIT: str = "10/minute"
    MAX_GEMINI_CALLS_PER_MINUTE: int = 5
    MAX_WEATHER_CALLS_PER_MINUTE: int = 10

    # External APIs
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    WEATHER_API_KEY: str = Field(default="", description="Weather API key")
    WEATHER_API_BASE_URL: str = Field(default="", description="Weather API base URL")

    # Database
    DATABASE_URL: str = "sqlite:///./relocation.db"

    # Cache
    CACHE_TTL_SECONDS: int = 600

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def get_settings() -> Settings:
    """Get settings singleton. Fails fast if required keys are missing."""
    return Settings()
