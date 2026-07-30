from typing import Literal

from pydantic import BaseModel, Field

TAG_IDS = ["ai-model", "ai-skill", "ai-tools", "api-mcp", "system-design",
           "uiux", "dataset", "soft-skills", "survey", "other"]

TagId = Literal["ai-model", "ai-skill", "ai-tools", "api-mcp", "system-design",
                "uiux", "dataset", "soft-skills", "survey", "other"]


class RawComment(BaseModel):
    id: str
    author: str
    author_role: str = "Học viên"
    content: str
    created_at: str


class RawPost(BaseModel):
    message_id: str
    channel: str
    title: str
    content: str
    author: str
    author_role: str = "Học viên"
    jump_url: str = ""
    created_at: str
    hearts: int = 0
    comments: list[RawComment] = Field(default_factory=list)


class NewsEnrichment(BaseModel):
    summary_vi: str
    tags: list[TagId] = Field(min_length=1, max_length=3)
    image_query: str
    image_url: str | None = None
