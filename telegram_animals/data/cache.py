import dataclasses
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Union

from dateutil import parser


class ChannelCache(ABC):
    @property
    @abstractmethod
    def date_checked(self) -> Optional[datetime]:
        pass

    @property
    @abstractmethod
    def gif_count(self) -> Optional[int]:
        pass

    @property
    @abstractmethod
    def pic_count(self) -> Optional[int]:
        pass

    @property
    @abstractmethod
    def video_count(self) -> Optional[int]:
        pass

    @property
    @abstractmethod
    def post_count(self) -> Optional[int]:
        pass

    @property
    @abstractmethod
    def subscribers(self) -> Optional[int]:
        pass

    @property
    @abstractmethod
    def latest_post(self) -> Optional[datetime]:
        pass

    @abstractmethod
    def to_json(self) -> Dict:
        raise NotImplementedError

    @classmethod
    def from_json(cls, json_cache: Dict) -> "ChannelCache":
        raise NotImplementedError


class TelegramCache(ChannelCache):

    def __init__(
            self,
            date_checked: datetime,
            channel_id: int,
            channel_hash: int,
            gif_count: int,
            pic_count: int,
            video_count: int,
            subscribers: int,
            latest_post: Optional[datetime],
            bio: Optional[str],
            title: Optional[str],
    ) -> None:
        self._date_checked = date_checked
        self.channel_id = channel_id
        self.channel_hash = channel_hash
        self._gif_count = gif_count
        self._pic_count = pic_count
        self._video_count = video_count
        self._subscribers = subscribers
        self._latest_post = latest_post
        self.bio = bio
        self.title = title

    @property
    def date_checked(self) -> datetime:
        return self._date_checked

    @property
    def gif_count(self) -> int:
        return self._gif_count

    @property
    def pic_count(self) -> int:
        return self._pic_count

    @property
    def video_count(self) -> int:
        return self._video_count

    @property
    def subscribers(self) -> int:
        return self._subscribers

    @property
    def latest_post(self) -> Optional[datetime]:
        return self._latest_post

    @property
    def post_count(self) -> Optional[int]:
        return None  # TODO

    def to_json(self) -> Dict[str, Union[str, int]]:
        return {
            "date_checked": self.date_checked.isoformat(),
            "gif_count": self.gif_count,
            "pic_count": self.pic_count,
            "video_count": self.video_count,
            "subscriber_count": self.subscribers,
            "latest_post": self.latest_post.isoformat() if self.latest_post else None,
            "channel_id": self.channel_id,
            "channel_hash": self.channel_hash,
            "bio": self.bio,
            "title": self.title
        }

    @classmethod
    def from_json(cls, json_cache: Dict[str, Optional[Union[str, int]]]) -> 'TelegramCache':
        return TelegramCache(
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


class TwitterCache(ChannelCache):
    def __init__(
            self,
            date_checked: datetime,
            handle: str,
            user_id: int,
            display_name: int,
            bio: str,
            user_location: str,
            user_url: str,
            creation_datetime: datetime,
            subscribers: int,
            post_count: int,
            latest_post: datetime,
            sample: "TwitterSample" = None,
    ):
        self._date_checked = date_checked
        self.handle = handle
        self.user_id = user_id
        self.display_name = display_name
        self.bio = bio
        self.user_location = user_location
        self.user_url = user_url
        self.creation_datetime = creation_datetime
        self._subscribers = subscribers
        self._post_count = post_count
        self._latest_post = latest_post
        self.sample = sample or TwitterSample()

    @property
    def date_checked(self) -> Optional[datetime]:
        return self._date_checked

    @property
    def gif_count(self) -> Optional[int]:
        if self.sample is None:
            return None
        gifs_per_tweet = self.sample.num_gifs / self.sample.num_tweets
        return int(gifs_per_tweet * self._post_count)

    @property
    def pic_count(self) -> Optional[int]:
        if self.sample is None:
            return None
        pics_per_tweet = self.sample.num_pics / self.sample.num_tweets
        return int(pics_per_tweet * self._post_count)

    @property
    def video_count(self) -> Optional[int]:
        if self.sample is None:
            return None
        vids_per_tweet = self.sample.num_vids / self.sample.num_tweets
        return int(vids_per_tweet * self._post_count)

    @property
    def post_count(self) -> int:
        return self._post_count

    @property
    def subscribers(self) -> int:
        return self._subscribers

    @property
    def latest_post(self) -> Optional[datetime]:
        return self._latest_post

    def to_json(self) -> Dict:
        pass  # TODO

    @classmethod
    def from_json(cls, json_cache: Dict) -> "ChannelCache":
        pass  # TODO


@dataclasses.dataclass
class TwitterSample:
    num_tweets: int = 0
    latest_id: int = None
    latest_datetime: datetime = None
    earliest_id: int = None
    earliest_datetime: datetime = None
    num_pics: int = 0
    num_vids: int = 0
    num_gifs: int = 0
    num_other_media: int = 0
    num_pic_tweets: int = 0
    num_no_media_tweets: int = 0
