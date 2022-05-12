import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import os

import pytz
from dateutil import parser

from telegram_animals.data.cache import TelegramCache, TwitterCache, ChannelCache


class ChannelType(Enum):
    TELEGRAM = "telegram"
    TWITTER = "twitter"

    @property
    def link_base(self) -> str:
        return {
            ChannelType.TELEGRAM: "https://t.me/",
            ChannelType.TWITTER: f"https://twitter.com/"
        }[self]

    def link(self, handle: str) -> str:
        return f"{self.link_base}{handle}"


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

    def to_javascript_data(self, cache: Optional[ChannelCache]) -> Dict[str, str]:
        latest_post = cache.latest_post if cache else None
        if latest_post:
            latest_post = latest_post.strftime("%Y-%m-%d")
        link = self.channel_type.link(self.handle)
        return {
            "platform": self.channel_type.value,
            "link": link,
            "handle": self.handle,
            "animal": self.animal,
            "owner": self.owner,
            "owner_html": self.owner_html,
            "num_posts": cache.post_count if cache else None,
            "num_pics": cache.pic_count if cache else None,
            "num_gifs": cache.gif_count if cache else None,
            "num_vids": cache.video_count if cache else None,
            "num_subs": cache.subscribers if cache else None,
            "latest_post": latest_post,
            "notes": self.notes,
            "notes_html": self.notes_html
        }

    def get_cache(self, datastore: "Datastore") -> Optional["TelegramCache"]:
        return datastore.fetch_cache(self.channel_type, self.handle)

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

    @property
    def notes_html(self) -> str:
        link_regex = re.compile(r"https://.+?(?=[,\s\"]|$)")
        handle_regex = re.compile("@(.+?)(?=[,\s\"]|$)")
        notes = self.notes
        for match in link_regex.finditer(notes):
            notes = notes.replace(
                match.group(0),
                f"<a href=\"{match.group(0)}\" target=\"_blank\">{match.group(0)}</a>"
            )
        for match in handle_regex.finditer(notes):
            notes = notes.replace(
                match.group(0),
                f"<a href=\"{self.channel_type.link(match.group(1))}\" target=\"_blank\">{match.group(0)}</a>"
            )
        return notes

    @property
    def owner_html(self) -> str:
        if self.owner.startswith("@") and all(char not in self.owner for char in [" ", ",", "\""]):
            owner_handle = self.owner[1:]
            return f"<a href=\"{self.channel_type.link(owner_handle)}\" target=\"_blank\">{self.owner}</a>"
        return self.owner


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
        # Telegram data cache
        try:
            with open("cache/channel_cache.json") as f:
                channel_cache = json.load(f)
        except FileNotFoundError:
            self._telegram_cache = {}
        else:
            self._telegram_cache = {
                handle: TelegramCache.from_json(value)
                for handle, value in channel_cache.items()
            }
        # Twitter data cache
        try:
            with open("cache/twitter_cache.json") as f:
                feed_cache = json.load(f)
        except FileNotFoundError:
            self._twitter_cache = {}
        else:
            self._twitter_cache = {
                handle: TwitterCache.from_json(value)
                for handle, value in feed_cache.items()
            }
        # Telegram search cache
        try:
            with open("cache/search_cache.json") as f:
                self.telegram_search_cache = json.load(f)
        except FileNotFoundError:
            self.telegram_search_cache = {"cache": {}}

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

    @property
    def list_animals(self) -> List[str]:
        return list(self.animal_data.keys())

    @property
    def list_animals_with_channels(self) -> List[str]:
        return [
            animal for animal in self.list_animals
            if any(channel.animal == animal for channel in self.all_channels)
        ]

    def fetch_cache(self, platform: ChannelType, handle: str) -> Optional[ChannelCache]:
        if platform == ChannelType.TELEGRAM:
            return self.fetch_telegram_cache(handle)
        if platform == ChannelType.TWITTER:
            return self.fetch_twitter_cache(handle)
        return None

    def fetch_telegram_cache(self, handle: str) -> Optional[TelegramCache]:
        return self._telegram_cache.get(handle.casefold())
    
    def update_telegram_cache(self, handle: str, cache: TelegramCache) -> None:
        self._telegram_cache[handle.casefold()] = cache

    def save_telegram_cache(self) -> None:
        json_cache = {
            handle: channel_cache.to_json()
            for handle, channel_cache in self._telegram_cache.items()
        }
        os.makedirs("cache", exist_ok=True)
        with open("cache/channel_cache.json", "w+") as f:
            json.dump(json_cache, f, indent=2)

    def fetch_twitter_cache(self, handle: str) -> Optional[TwitterCache]:
        return self._twitter_cache.get(handle.casefold())

    def update_twitter_cache(self, handle: str, cache: TwitterCache) -> None:
        self._twitter_cache[handle.casefold()] = cache

    def save_twitter_cache(self) -> None:
        json_cache = {
            handle: channel_cache.to_json()
            for handle, channel_cache in self._twitter_cache.items()
        }
        os.makedirs("cache", exist_ok=True)
        with open("cache/twitter_cache.json", "w+") as f:
            json.dump(json_cache, f, indent=2)
