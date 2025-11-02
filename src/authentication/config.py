"""
Centralizes configuration parameters for the application,
including security-critical settings for password hashing.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation.
    """

    # Application settings
    APP_NAME: str = "StArranja"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database settings
    DATABASE_URL: str | None = None

    # Password Hashing Configuration
    ARGON2_TIME_COST: int = Field(default=3, description="Number of iterations (recommended: 2-4 for Argon2id)")

    ARGON2_MEMORY_COST: int = Field(
        default=65536,  # 64 MiB
        description="Memory usage in KiB (recommended: 65536 KiB = 64 MiB)",
    )

    ARGON2_PARALLELISM: int = Field(default=4, description="Number of parallel threads (recommended: 4)")

    ARGON2_HASH_LENGTH: int = Field(default=32, description="Length of the hash in bytes")

    ARGON2_SALT_LENGTH: int = Field(default=16, description="Length of the salt in bytes")

    # Password Policy
    MIN_PASSWORD_LENGTH: int = Field(default=8, description="Minimum password length")

    MAX_PASSWORD_LENGTH: int = Field(default=128, description="Maximum password length")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

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


# Global settings instance
settings = Settings()
