from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    linkedin_li_at: SecretStr | None = Field(default=None, validation_alias="LINKEDIN_LI_AT")
    linkedin_jsessionid: SecretStr | None = Field(
        default=None, validation_alias="LINKEDIN_JSESSIONID"
    )
    linkedin_csrf_token: SecretStr | None = Field(
        default=None, validation_alias="LINKEDIN_CSRF_TOKEN"
    )
    linkedin_timeout_seconds: float = Field(
        default=20.0, validation_alias="LINKEDIN_TIMEOUT_SECONDS", ge=1, le=60
    )
    linkedin_min_interval_seconds: float = Field(
        default=2.0, validation_alias="LINKEDIN_MIN_INTERVAL_SECONDS", ge=0, le=60
    )
    linkedin_section_delay_seconds: float = Field(
        default=1.5, validation_alias="LINKEDIN_SECTION_DELAY_SECONDS", ge=0, le=10
    )
    profile_cache_ttl_seconds: float = Field(
        default=30.0, validation_alias="PROFILE_CACHE_TTL_SECONDS", ge=0, le=300
    )
    rate_limit_per_ip: int = Field(default=10, validation_alias="RATE_LIMIT_PER_IP", ge=1)
    rate_limit_global: int = Field(default=60, validation_alias="RATE_LIMIT_GLOBAL", ge=1)
    rate_limit_window_seconds: int = Field(
        default=60, validation_alias="RATE_LIMIT_WINDOW_SECONDS", ge=1
    )

    @property
    def linkedin_configured(self) -> bool:
        return bool(
            self.linkedin_li_at
            and self.linkedin_li_at.get_secret_value()
            and self.linkedin_jsessionid
            and self.linkedin_jsessionid.get_secret_value()
        )

    @property
    def csrf_token(self) -> str:
        if self.linkedin_csrf_token and self.linkedin_csrf_token.get_secret_value():
            return self.linkedin_csrf_token.get_secret_value().strip('"')
        if not self.linkedin_jsessionid:
            return ""
        return self.linkedin_jsessionid.get_secret_value().strip('"')


@lru_cache
def get_settings() -> Settings:
    return Settings()
