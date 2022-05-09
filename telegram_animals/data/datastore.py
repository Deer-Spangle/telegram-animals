import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import os

import pytz
from dateutil import parser

from telegram_animals.data.cache import TelegramCache, TwitterCache


class ChannelType(Enum):
    TELEGRAM = "telegram"
    TWITTER = "twitter"


@dataclass
class Channel:
    handle: str
    animal: str
    owner: str
    notes: str
    handle_pattern: str
    channel_type: ChannelType = ChannelType.TELEGRAM
    removal_reason: Optional[str] = None

    @classmethod
    def from_json(cls, data, channel_type: ChannelType = ChannelType.TELEGRAM) -> 'Channel':
        return cls(
            data["handle"],
            data["animal"],
            data["owner"],
            data["notes"],
            data["handle_pattern"],
            channel_type=channel_type,
            removal_reason=data.get("removal_reason")
        )

    def to_javascript_data(self, datastore: "Datastore") -> Dict[str, str]:
        cache = self.get_cache(datastore)
        latest_post = getattr(cache, "latest_post", None)
        if latest_post:
            latest_post = latest_post.strftime("%Y-%m-%d")
        link = {
            ChannelType.TELEGRAM: f"https://t.me/{self.handle}",
            ChannelType.TWITTER: f"https://twitter.com/{self.handle}"
        }[self.channel_type]
        return {
            "platform": self.channel_type.value,
            "link": link,
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

    def get_cache(self, datastore: "Datastore") -> Optional["TelegramCache"]:
        if self.channel_type == ChannelType.TELEGRAM:
            return datastore.telegram_cache.get(self.handle.casefold())
        return None

    @property
    def is_bot(self) -> bool:
        return self.handle.lower().endswith("bot")

    @property
    def is_removed(self) -> bool:
        return self.removal_reason is not None

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


class Datastore:
    def __init__(self):
        # Animal data
        with open("store/animals.json") as f:
            self.animal_data: Dict[str, List[str]] = json.load(f)
        # Telegram data
        with open("store/telegram.json") as f:
            telegram_data = json.load(f)
            self.telegram_entities = [Channel.from_json(entity) for entity in telegram_data["entities"]]
            self.telegram_removed = [Channel.from_json(entity) for entity in telegram_data["removed"]]
            self.telegram_ignored = [Ignore.from_json(ignore) for ignore in telegram_data["ignored"]]
        # Twitter data
        with open("store/twitter.json") as f:
            twitter_data = json.load(f)
            self.twitter_feeds = [Channel.from_json(entity, ChannelType.TWITTER) for entity in twitter_data["entities"]]
        # Telegram cache
        try:
            with open("cache/channel_cache.json") as f:
                channel_cache = json.load(f)
        except FileNotFoundError:
            self.telegram_cache = {}
        else:
            self.telegram_cache = {
                handle: TelegramCache.from_json(value)
                for handle, value in channel_cache.items()
            }
        # Telegram search cache
        try:
            with open("cache/search_cache.json") as f:
                self.telegram_search_cache = json.load(f)
        except FileNotFoundError:
            self.telegram_search_cache = {"cache": {}}
        # Twitter cache
        try:
            with open("cache/twitter_cache.json") as f:
                feed_cache = json.load(f)
        except FileNotFoundError:
            self.twitter_cache = {}
        else:
            self.twitter_cache = {
                handle: TwitterCache.from_json(value)
                for handle, value in feed_cache.items()
            }

    @property
    def all_channels(self) -> List[Channel]:
        return self.telegram_channels + self.twitter_feeds

    @property
    def telegram_channels(self) -> List[Channel]:
        return [
            channel for channel in self.telegram_entities if not channel.is_bot
        ]

    @property
    def telegram_bots(self) -> List[Channel]:
        return [
            channel for channel in self.telegram_entities if channel.is_bot
        ]

    def save_telegram_cache(self) -> None:
        json_cache = {
            handle: channel_cache.to_json()
            for handle, channel_cache in self.telegram_cache.items()
        }
        os.makedirs("cache", exist_ok=True)
        with open("cache/channel_cache.json", "w+") as f:
            json.dump(json_cache, f, indent=2)

    @property
    def list_animals(self) -> List[str]:
        return list(self.animal_data.keys())

    @property
    def list_animals_with_channels(self) -> List[str]:
        return [
            animal for animal in self.list_animals
            if any(channel.animal == animal for channel in self.all_channels)
        ]

    def fetch_twitter_cache(self, handle: str) -> Optional[TwitterCache]:
        return self.twitter_cache.get(handle.casefold())

    def update_twitter_cache(self, handle: str, cache: TwitterCache) -> None:
        self.twitter_cache[handle.casefold()] = cache

    def save_twitter_cache(self) -> None:
        json_cache = {
            handle: channel_cache.to_json()
            for handle, channel_cache in self.twitter_cache.items()
        }
        os.makedirs("cache", exist_ok=True)
        with open("cache/twitter_cache.json", "w+") as f:
            json.dump(json_cache, f, indent=2)
