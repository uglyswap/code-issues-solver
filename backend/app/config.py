from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql+asyncpg://app:changeme@localhost:5432/code_issues_solver")
    redis_url: str = Field(default="redis://localhost:6379/0")
    encryption_key: str = Field(default="base64encoded32byteskey==")
    jwt_secret: str = Field(default="supersecretjwtkeychangeme")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)
    cors_origins: List[str] = Field(default=["http://localhost:3500", "http://localhost:3501", "http://207.180.243.246:3500"])
    log_level: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_encryption_key_bytes(self) -> bytes:
        return self.encryption_key.encode()


settings = Settings()
