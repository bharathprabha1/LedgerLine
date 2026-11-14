
from functools import lru_cache
from typing import Literal

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LedgerLine"

    app_env: Literal[
        "development",
        "testing",
        "production",
    ] = "development"

    debug: bool = False

    database_url: str = Field(min_length=1)
    secret_key: SecretStr

    jwt_algorithm: Literal["HS256"] = "HS256"

    access_token_expire_minutes: int = Field(
        default=15,
        gt=0,
        le=1440,
    )

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174"
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()

        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Database URL cannot be empty")

        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]

        if not origins:
            raise ValueError(
                "At least one CORS origin must be configured"
            )

        return ",".join(origins)

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env == "production":
            if self.debug:
                raise ValueError(
                    "Debug mode must be disabled in production"
                )

            secret = self.secret_key.get_secret_value()

            if len(secret) < 32:
                raise ValueError(
                    "Production SECRET_KEY must contain at least 32 characters"
                )

            if secret == "REPLACE_WITH_RANDOM_SECRET":
                raise ValueError(
                    "Production SECRET_KEY must be replaced"
                )

            if "*" in self.allowed_origins:
                raise ValueError(
                    "Wildcard CORS origins are not allowed in production"
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
