from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

Platform = Literal["xiaohongshu", "douyin", "bilibili"]
Short = Annotated[str, Field(min_length=1, max_length=120)]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(DTO):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)


class Register(Credentials):
    name: Short


class FactInput(DTO):
    claim: str = Field(min_length=1, max_length=1000)
    source: str = Field(min_length=1, max_length=2000)
    verified: bool = False


class BrandInput(DTO):
    name: Short
    description: str = Field(default="", max_length=5000)
    audience: str = Field(default="", max_length=2000)
    website: str = Field(default="", max_length=2000)
    facts: list[FactInput] = Field(default_factory=list, max_length=100)

    @field_validator("website")
    @classmethod
    def website_safe(cls, value):
        if value and (urlsplit(value).scheme != "https" or not urlsplit(value).hostname):
            raise ValueError("官网使用完整 HTTPS 地址")
        return value


class RenderOptions(DTO):
    graphics: bool = False
    video: bool = False
    duration_sec: int = Field(default=30, ge=3, le=60)
    video_mode: Literal["mg", "mixed", "screen_demo", "montage"] = "mg"
    size: Literal["wide", "portrait", "square"] = "wide"
    asset_id: Short | None = None


class CreatorInput(DTO):
    brand_id: Short
    name: Short
    timezone: str = "Asia/Shanghai"
    hour: int = Field(default=9, ge=0, le=23)
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    style: str = Field(default="简洁、可信、不夸张", max_length=1000)
    platform: Platform = "xiaohongshu"
    daily_budget_cents: int = Field(default=500, ge=0, le=1000000)
    monthly_budget_cents: int = Field(default=10000, ge=0, le=10000000)
    model_consent: bool = False
    render_options: RenderOptions | None = None

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("时区无效") from None
        return value

    @field_validator("weekdays")
    @classmethod
    def valid_days(cls, days):
        if any(d < 0 or d > 6 for d in days) or len(set(days)) != len(days):
            raise ValueError("星期取值 0–6 且不重复")
        return days


class CopyVariant(DTO):
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=12000)
    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(
        default_factory=list, max_length=10
    )


class ContentPatch(DTO):
    expected_revision: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=180)
    body: str | None = Field(default=None, min_length=1, max_length=12000)
    variants: dict[Platform, CopyVariant] | None = None
    reason_tag: Literal[
        "edit", "too_advertising", "inaccurate", "too_fast", "more_real", "inconsistent", "shorter", "other"
    ] = "edit"


class Approve(DTO):
    confirmed: Literal[True]
    expected_revision: int | None = Field(default=None, ge=1)


class HandoffInput(DTO):
    content_id: Short
    expected_revision: int | None = Field(default=None, ge=1)


class PublicationInput(DTO):
    package_id: Short
    published_at: datetime
    url: str = Field(default="", max_length=2048)
    notes: str = Field(default="", max_length=2000)
    checklist: list[Literal[True]] = Field(min_length=5, max_length=5)

    @field_validator("published_at")
    @classmethod
    def aware_date(cls, dt):
        if dt.tzinfo is None:
            raise ValueError("发布时间必须包括时区")
        return dt


class ImportCommit(DTO):
    preview_id: Short


class Shot(DTO):
    shot_id: Short
    shot_revision: int = Field(default=1, ge=1)
    provider: Literal["pillow_mg", "ffmpeg_media", "comfy_wan", "blender"]
    kind: Literal["motion_graphics", "screen_demo", "montage", "ai_creative_scene", "three_d"]
    duration_frames: int = Field(ge=15, le=1800)
    caption: str = Field(default="", max_length=180)
    asset_id: str | None = None
    locked: bool = False
    trim_start_frame: int = Field(default=0, ge=0, le=216000)
    speed_percent: int = Field(default=100, ge=25, le=400)


class AudioTrack(DTO):
    track_id: Short
    asset_id: Short
    role: Literal["voiceover", "music"]
    start_frame: int = Field(default=0, ge=0, le=3600)
    duration_frames: int = Field(ge=1, le=3600)
    source_start_frame: int = Field(default=0, ge=0, le=216000)
    volume_percent: int = Field(default=100, ge=0, le=200)
    loop: bool = False


class Subtitle(DTO):
    cue_id: Short
    start_frame: int = Field(ge=0, le=3600)
    end_frame: int = Field(ge=1, le=3600)
    text: str = Field(min_length=1, max_length=120)


class VideoInput(DTO):
    brand_id: Short
    name: Short
    width: Literal[1080, 1920] = 1920
    height: Literal[1080, 1920] = 1080
    fps: Literal[30] = 30
    shots: list[Shot] = Field(min_length=1, max_length=12)
    audio_tracks: list[AudioTrack] = Field(default_factory=list, max_length=8)
    subtitles: list[Subtitle] = Field(default_factory=list, max_length=100)
