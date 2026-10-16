"""Validated local configuration; no database connection at import time."""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FALKORDB_", env_file=".env", extra="ignore")

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=6379, ge=1, le=65535)
    graph: str = Field(default="rippleproof", pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    connect_timeout_s: float = Field(default=2, gt=0, le=10)
    socket_timeout_s: float = Field(default=5, gt=0, le=30)
    query_timeout_ms: int = Field(default=3000, ge=1, le=20000)


class Phase3Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RIPPLEPROOF_", env_file=".env", extra="ignore")

    approval_secret: SecretStr | None = Field(default=None, min_length=32, max_length=256)
    provider: Literal["disabled", "openai"] = "disabled"
    allow_paid_calls: bool = False
    openai_api_key: SecretStr | None = None
    openai_model: str | None = Field(default=None, min_length=1, max_length=100)
    model_timeout_s: float = Field(default=20, gt=0, le=30)
    run_timeout_s: float = Field(default=90, ge=1, le=120)
    max_turns: int = Field(default=6, ge=1, le=8)
    max_tool_calls: int = Field(default=8, ge=1, le=12)

    @field_validator("approval_secret", "openai_api_key", "openai_model", mode="before")
    @classmethod
    def empty_optional(cls, value):
        return None if value == "" else value
