from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Ayunadi CRM Services"
    APP_VERSION: str = "1.0.0"
    ENV: str = "dev"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str
    CORS_ORIGINS: List[AnyHttpUrl] = []
    UPLOAD_DIR: str = "upload"
    FONNTE_TOKEN: str = ""
    OTP_EXPIRE_MINUTES: int = 5
    SHOW_DOCS: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()