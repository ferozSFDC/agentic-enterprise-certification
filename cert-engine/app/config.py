from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://cat:cat@localhost:5432/cat_engine"
    database_url_sync: str = "postgresql://cat:cat@localhost:5432/cat_engine"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    admin_api_key: str = "change-me-in-production"

    # CAT defaults (can be overridden by exam_configs table)
    default_theta_c: float = 0.0
    default_delta: float = 0.2
    default_alpha: float = 0.05
    default_beta: float = 0.05
    default_max_items: int = 40
    default_min_items: int = 5
    default_starting_theta: float = 0.0
    default_w_info: float = 0.7
    default_w_content: float = 0.3
    default_max_exposure_rate: float = 0.25
    default_time_limit_minutes: int = 120

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = {"env_prefix": "CAT_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
