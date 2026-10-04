from abc import ABC, abstractmethod

from app.models import Video


class Provider(ABC):
    """A source of video data.

    Implement this for a licensed data API (Apify, Bright Data, EnsembleData...)
    or the official TikTok Research / Instagram Graph APIs. Analytics and the
    API never depend on where the data came from.
    """

    name: str

    @abstractmethod
    def fetch_trending(self, platform: str, limit: int = 100) -> list[Video]: ...

    @abstractmethod
    def fetch_hashtag(self, platform: str, tag: str, limit: int = 100) -> list[Video]: ...
