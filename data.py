import json
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Union
import os

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

    @property
    def is_bot(self) -> bool:
        return self.handle.lower().endswith("bot")

    def __eq__(self, other):
        return isinstance(other, Channel) and self.handle.casefold() == other.handle.casefold()

    def __hash__(self):
        return hash(self.handle.casefold())


def load_channels_and_bots() -> Tuple[List[Channel], List[Channel]]:
    with open("telegram.json", "r") as f:
        data_store = json.load(f)
    sorted_entites = sorted([
        Channel.from_json(channel_data)
        for channel_data in data_store["entities"]
    ], key=lambda c: (c.animal, c.handle))
    return (
        [channel for channel in sorted_entites if not channel.is_bot],
        [bot for bot in sorted_entites if bot.is_bot]
    )


def load_channels() -> List[Channel]:
    return [entity for entity in load_entities() if not entity.is_bot]


def load_entities() -> List[Channel]:
    with open("telegram.json", "r") as f:
        telegram_data = json.load(f)
    return [Channel.from_json(entity_datum) for entity_datum in telegram_data["entities"]]


def load_animals() -> Dict[str, List[str]]:
    with open("animals.json", "r") as f:
        return json.load(f)


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

    def to_json(self) -> Dict[str, Union[str, int]]:
        return {
            "date_checked": self.date_checked.isoformat(),
            "channel_id": self.channel_id,
            "channel_hash": self.channel_hash,
            "gif_count": self.gif_count,
            "pic_count": self.pic_count,
            "video_count": self.video_count,
            "subscriber_count": self.subscribers,
            "latest_post": self.latest_post.isoformat() if self.latest_post else None
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
            parser.parse(json_cache["latest_post"]) if json_cache["latest_post"] else None
        )


def save_channel_cache(cache: Dict[Channel, ChannelCache]):
    json_cache = {
        channel.handle.casefold(): channel_cache.to_json()
        for channel, channel_cache in cache.items()
    }
    os.makedirs("cache", exist_ok=True)
    with open("cache/channel_cache.json", "w+") as f:
        json.dump(json_cache, f, indent=2)


def load_channel_cache() -> Dict[str, ChannelCache]:
    with open("cache/channel_cache.json", "r") as f:
        json_cache = json.load(f)
    return {
        handle: ChannelCache.from_json(value)
        for handle, value in json_cache.items()
    }
