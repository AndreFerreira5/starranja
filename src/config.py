"""
Centralizes configuration parameters for the application,
including security settings for hashing and token management.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseModel):
    ARGON2_TIME_COST: int = Field(
        default=3, description="Number of iterations (recommended: 2-4 for Argon2id)"
    )

    ARGON2_MEMORY_COST: int = Field(
        default=65536,  # 64 MiB
        description="Memory usage in KiB (recommended: 65536 KiB = 64 MiB)",
    )

    ARGON2_PARALLELISM: int = Field(
        default=4, description="Number of parallel threads (recommended: 4)"
    )

    ARGON2_HASH_LENGTH: int = Field(
        default=32, description="Length of the hash in bytes"
    )

    ARGON2_SALT_LENGTH: int = Field(
        default=16, description="Length of the salt in bytes"
    )

    # Password Policy
    MIN_PASSWORD_LENGTH: int = Field(default=8, description="Minimum password length")
    MAX_PASSWORD_LENGTH: int = Field(default=128, description="Maximum password length")

    # ========================================================================
    # Token Configuration (PASETO)
    # ========================================================================

    PASETO_SECRET_KEY: str = Field(
        default="",
        description=(
            "PASETO symmetric key (must be exactly 64 hex characters / 32 bytes)"
        ),
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Access token expiration time in minutes (default: 15 minutes)",
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration time in days (default: 7 days)",
    )

    @field_validator("ARGON2_TIME_COST")
    @classmethod
    def validate_time_cost(cls, v: int) -> int:
        """Validate time cost is in reasonable range."""
        if v < 1 or v > 10:
            raise ValueError("Time cost must be between 1 and 10")
        return v

    @field_validator("ARGON2_MEMORY_COST")
    @classmethod
    def validate_memory_cost(cls, v: int) -> int:
        """Validate memory cost is in reasonable range."""
        if v < 8192 or v > 2097152:  # 8 MiB to 2 GiB
            raise ValueError("Memory cost must be between 8192 and 2097152 KiB")
        return v

    @field_validator("ARGON2_PARALLELISM")
    @classmethod
    def validate_parallelism(cls, v: int) -> int:
        """Validate parallelism is in reasonable range."""
        if v < 1 or v > 16:
            raise ValueError("Parallelism must be between 1 and 16")
        return v

    @field_validator("MIN_PASSWORD_LENGTH")
    @classmethod
    def validate_min_password_length(cls, v: int) -> int:
        """Validate minimum password length."""
        if v < 8:
            raise ValueError("Minimum password length should be at least 8")
        return v

    # ========================================================================
    # Token Configuration Validators
    # ========================================================================

    @field_validator("PASETO_SECRET_KEY")
    @classmethod
    def validate_paseto_key(cls, v: str) -> str:
        """
        Validate PASETO secret key format and length.

        Must be exactly 64 hexadecimal characters (32 bytes).
        """
        if not isinstance(v, str):
            raise ValueError("PASETO_SECRET_KEY must be a string")

        # Remove whitespace
        v = v.strip()

        # Check length (64 hex chars = 32 bytes)
        if len(v) != 64:
            raise ValueError(
                "PASETO_SECRET_KEY must be exactly 64 hexadecimal characters "
                "(32 bytes). Use: python -c 'import secrets; "
                "print(secrets.token_hex(32))' to generate one"
            )

        # Validate hex format
        try:
            bytes.fromhex(v)
        except ValueError as e:
            raise ValueError(
                "PASETO_SECRET_KEY must contain only hexadecimal characters (0-9, a-f)"
            ) from e

        return v

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_access_token_expiration(cls, v: int) -> int:
        """
        Validate access token expiration time.

        Should be between 1 minute and 24 hours (1440 minutes).
        """
        if v < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1")
        if v > 1440:  # 24 hours
            raise ValueError(
                "ACCESS_TOKEN_EXPIRE_MINUTES should not exceed 1440 (24 hours)"
            )
        return v

    @field_validator("REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_refresh_token_expiration(cls, v: int) -> int:
        """
        Validate refresh token expiration time.

        Should be between 1 day and 90 days.
        """
        if v < 1:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be at least 1")
        if v > 90:
            raise ValueError(
                "REFRESH_TOKEN_EXPIRE_DAYS should not exceed 90 days for security"
            )
        return v


class DatabaseSettings(BaseModel):
    # Database settings
    AUTH_DATABASE_URL: str | None = None


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "StArranja"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
