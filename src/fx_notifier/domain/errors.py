class FXServiceError(Exception):
    """Raised when FX data cannot be fetched or normalized safely."""


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""
