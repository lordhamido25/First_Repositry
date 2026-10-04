import os

from app.providers.base import Provider
from app.providers.mock import MockProvider


def get_provider() -> Provider:
    """Pick a provider via TRENDSCOPE_PROVIDER. Add real ones here."""
    name = os.getenv("TRENDSCOPE_PROVIDER", "mock")
    if name == "mock":
        return MockProvider()
    raise ValueError(f"Unknown provider {name!r}; implement it in app/providers/")
