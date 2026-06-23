from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
import os
import warnings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql+asyncpg://app:changeme@localhost:5432/code_issues_solver")
    redis_url: str = Field(default="redis://localhost:6379/0")
    encryption_key: str = Field(default="base64encoded32byteskey==")
    jwt_secret: str = Field(default="supersecretjwtkeychangeme")
    github_webhook_secret: str = Field(default="changeme_webhook_secret")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)
    cors_origins: List[str] = Field(default=["http://localhost:3500", "http://localhost:3501", "http://207.180.243.246:3500"])
    log_level: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("encryption_key", "jwt_secret", "github_webhook_secret")
    @classmethod
    def warn_weak_secrets(cls, v: str, info) -> str:
        weak_values = {"changeme", "supersecretjwtkeychangeme", "base64encoded32byteskey==", "changeme_webhook_secret"}
        if v in weak_values and os.environ.get("ENVIRONMENT") == "production":
            raise ValueError(f"Secret par défaut détecté pour {info.field_name} — définissez les variables d'environnement en production")
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        weak = {
            "encryption_key": self.encryption_key == "base64encoded32byteskey==",
            "jwt_secret": self.jwt_secret == "supersecretjwtkeychangeme",
            "github_webhook_secret": self.github_webhook_secret == "changeme_webhook_secret",
        }
        if any(weak.values()):
            warnings.warn(
                f"⚠️ Secrets par défaut détectés: {[k for k,v in weak.items() if v]}. "
                "Définissez les variables d'environnement en production!",
                RuntimeWarning
            )

    def get_encryption_key_bytes(self) -> bytes:
        return self.encryption_key.encode()


settings = Settings()
