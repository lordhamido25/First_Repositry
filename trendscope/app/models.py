from datetime import datetime

from pydantic import BaseModel, Field


class Video(BaseModel):
    """Platform-neutral short-video record. Every provider maps into this."""

    id: str
    platform: str  # "tiktok" | "instagram"
    author: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    sound: str | None = None
    posted_at: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    author_followers: int = 0
