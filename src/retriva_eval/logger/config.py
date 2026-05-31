from pydantic_settings import BaseSettings, SettingsConfigDict

class LoggerSettings(BaseSettings):
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

logger_settings = LoggerSettings()
