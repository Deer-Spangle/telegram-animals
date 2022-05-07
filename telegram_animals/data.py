import json
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Union
import os

import pytz
from dateutil import parser


@dataclass
class Channel:
    handle: str
    animal: str
    owner: str
    notes: str
    handle_pattern: str

    @classmethod
    def from_json(cls, data) -> 'Channel':
        return cls(
            data["handle"],
            data["animal"],
            data["owner"],
            data["notes"],
            data["handle_pattern"]
        )

    def to_javascript_data(self, channel_cache: Dict[str, "ChannelCache"]) -> Dict[str, str]:
        cache = channel_cache.get(self.handle.casefold())
        latest_post = getattr(cache, "latest_post", None)
        if latest_post:
            latest_post = latest_post.strftime("%Y-%m-%d")
        return {
            "type": "telegram_channel",
            "link": f"https://t.me/{self.handle}",
            "handle": self.handle,
            "animal": self.animal,
            "owner": self.owner,
            "num_pics": getattr(cache, "pic_count", None),
            "num_gifs": getattr(cache, "gif_count", None),
            "num_vids": getattr(cache, "video_count", None),
            "num_subs": getattr(cache, "subscribers", None),
            "latest_post": latest_post,
            "notes": self.notes
        }

    @property
    def is_bot(self) -> bool:
        return self.handle.lower().endswith("bot")

    def __eq__(self, other):
        return isinstance(other, Channel) and self.handle.casefold() == other.handle.casefold()

    def __hash__(self):
        return hash(self.handle.casefold())


@dataclass
class Ignore:
    handle: str
    reason: str
    expiry: Optional[datetime] = None

    @classmethod
    def from_json(cls, data: Dict) -> 'Ignore':
        return cls(
            data["handle"],
            data["reason"],
            None if "expiry" not in data else parser.parse(data["expiry"])
        )

    @property
    def is_expired(self) -> bool:
        if self.expiry is None:
            return False
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        return now > self.expiry


def load_channels_and_bots() -> Tuple[List[Channel], List[Channel]]:
    with open("store/telegram.json", "r") as f:
        data_store = json.load(f)
    sorted_entites = sorted([
        Channel.from_json(channel_data)
        for channel_data in data_store["entities"]
    ], key=lambda c: (c.animal, c.handle.casefold()))
    return (
        [channel for channel in sorted_entites if not channel.is_bot],
        [bot for bot in sorted_entites if bot.is_bot]
    )


def load_channels() -> List[Channel]:
    return [entity for entity in load_entities() if not entity.is_bot]


def load_entities() -> List[Channel]:
    with open("store/telegram.json", "r") as f:
        telegram_data = json.load(f)
    return [Channel.from_json(entity_datum) for entity_datum in telegram_data["entities"]]


def load_animals() -> Dict[str, List[str]]:
    with open("store/animals.json", "r") as f:
        return json.load(f)


def load_ignored() -> List[Ignore]:
    with open("store/telegram.json", "r") as f:
        telegram_data = json.load(f)
    if "ignored" not in telegram_data:
        return []
    return [Ignore.from_json(ignore_data) for ignore_data in telegram_data["ignored"]]


@dataclass
class ChannelCache:
    date_checked: datetime
    channel_id: Optional[int]  # TODO: un-optional, once we have id & hash in cache
    channel_hash: Optional[int]
    gif_count: int
    pic_count: int
    video_count: int
    subscribers: int
    latest_post: Optional[datetime]
    bio: Optional[str]
    title: Optional[str]

    def to_json(self) -> Dict[str, Union[str, int]]:
        return {
            "date_checked": self.date_checked.isoformat(),
            "channel_id": self.channel_id,
            "channel_hash": self.channel_hash,
            "gif_count": self.gif_count,
            "pic_count": self.pic_count,
            "video_count": self.video_count,
            "subscriber_count": self.subscribers,
            "latest_post": self.latest_post.isoformat() if self.latest_post else None,
            "bio": self.bio,
            "title": self.title
        }

    @classmethod
    def from_json(cls, json_cache: Dict[str, Optional[Union[str, int]]]) -> 'ChannelCache':
        return ChannelCache(
            parser.parse(json_cache["date_checked"]),
            json_cache.get("channel_id"),
            json_cache.get("channel_hash"),
            json_cache["gif_count"],
            json_cache["pic_count"],
            json_cache["video_count"],
            json_cache["subscriber_count"],
            parser.parse(json_cache["latest_post"]) if json_cache["latest_post"] else None,
            json_cache.get("bio"),
            json_cache.get("title")
        )


def save_channel_cache(cache: Dict[str, ChannelCache]):
    json_cache = {
        handle: channel_cache.to_json()
        for handle, channel_cache in cache.items()
    }
    os.makedirs("cache", exist_ok=True)
    with open("cache/channel_cache.json", "w+") as f:
        json.dump(json_cache, f, indent=2)


def load_channel_cache() -> Dict[str, ChannelCache]:
    try:
        with open("cache/channel_cache.json", "r") as f:
            json_cache = json.load(f)
    except FileNotFoundError:
        return {}
    return {
        handle: ChannelCache.from_json(value)
        for handle, value in json_cache.items()
    }
