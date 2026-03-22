from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

    # Database
    database_url: str

    # Environment
    environment: str
    log_level: str = "INFO"
    enable_file_logging: bool = False

    # Feed reader
    feed_reader_max_concurrent_feeds: int = 4
    feed_reader_max_concurrent_entries: int = 50

    # HTTP client
    http_timeout: float = 30.0
    http_max_retries: int = 5
    http_retry_delay: float = 1.0

    # DB retry
    db_max_retries: int = 10
    db_retry_delay: float = 3.0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
