import datetime
import itertools
import json
import re
from argparse import Namespace
from dataclasses import dataclass
from typing import Optional, Dict, List, TypeVar, Callable, Tuple, Iterable

import pytz
import requests
from dateutil import parser
from bs4 import BeautifulSoup

from telegram_animals.data.datastore import Channel, Ignore, Datastore
from telegram_animals.subparser import SubParserAdder

T = TypeVar("T")


def split_list(source_list: Iterable[T], condition: Callable[[T], bool]) -> Tuple[List[T], List[T]]:
    """
    Splits a list by a condition.
    Returning the list of entries for which the condition is true, then the list of entries for which the
    condition is false.
    """
    true_list = []
    false_list = []
    for entry in source_list:
        if condition(entry):
            true_list.append(entry)
        else:
            false_list.append(entry)
    return true_list, false_list


@dataclass
class CachePostPreview:
    post_id: int
    date: datetime.datetime

    def to_json(self) -> Dict:
        return {
            "post_id": self.post_id,
            "date": self.date.isoformat()
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'CachePostPreview':
        return cls(
            data["post_id"],
            parser.parse(data["date"])
        )


@dataclass
class SearchCacheEntry:
    handle: str
    in_store: bool
    exists_in_telegram: Optional[bool]
    ignored: bool
    last_checked: Optional[datetime.datetime]
    latest_posts: Optional[List[CachePostPreview]]
    subscribers: Optional[int]

    def to_json(self) -> Dict:
        return {
            "handle": self.handle,
            "in_store": self.in_store,
            "exists_in_telegram": self.exists_in_telegram,
            "ignored": self.ignored,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "latest_posts": None if self.latest_posts is None else [post.to_json() for post in self.latest_posts],
            "subscribers": self.subscribers
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'SearchCacheEntry':
        return cls(
            data["handle"],
            data["in_store"],
            data["exists_in_telegram"],
            data["ignored"],
            parser.parse(data["last_checked"]) if data["last_checked"] else None,
            None if data.get("latest_posts") is None else [
                CachePostPreview.from_json(post_data) for post_data in data["latest_posts"]
            ],
            data.get("subscribers")
        )

    @property
    def is_known(self) -> bool:
        return self.in_store or self.ignored

    def older_than(self, age: datetime.timedelta, now: Optional[datetime.datetime] = None) -> bool:
        if self.last_checked is None:
            return True
        now = now or datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        my_age = now - self.last_checked
        return my_age > age

    def check_existence(self) -> bool:
        path = f"https://t.me/{self.handle}"
        resp = requests.get(path)
        assert resp.status_code == 200
        exists = f'href="/s/{self.handle}">Preview channel</a>' in resp.text
        self.exists_in_telegram = exists
        self.last_checked = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        if exists:
            self.check_subscribers(resp.text)
        return exists
    
    def check_subscribers(self, page_code: Optional[str] = None) -> Optional[int]:
        if not self.exists_in_telegram:
            return None
        page_code = page_code or requests.get(f"https://t.me/{self.handle}").text
        subs = re.search(
            r"<div class=\"(?:tgme_page_extra|tgme_header_counter)\">([0-9 ]+|no) subscribers?</div>",
            page_code
        )
        sub_str = subs.group(1)
        if sub_str == "no":
            self.subscribers = 0
        else:
            self.subscribers = int(sub_str.replace(" ", ""))
        return self.subscribers

    def check_posts(self) -> Optional[List[CachePostPreview]]:
        if not self.exists_in_telegram:
            return None
        path = f"https://t.me/s/{self.handle}"
        resp = requests.get(path)
        assert resp.status_code == 200
        # Find message divs
        soup = BeautifulSoup(resp.text, "html.parser")
        date_links = soup.find_all("a", {"class": "tgme_widget_message_date"})
        self.latest_posts = []
        for date_link in date_links:
            post_link = date_link["href"]
            post_id = int(post_link.split("/")[-1])
            post_time_tag = date_link.find("time")
            post_time = parser.parse(post_time_tag["datetime"])
            post = CachePostPreview(post_id, post_time)
            self.latest_posts.append(post)
        return self.latest_posts

    def has_post_newer_than(self, age: datetime.timedelta, now: Optional[datetime.datetime] = None) -> bool:
        if self.latest_posts is None:
            return False
        now = now or datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        if not self.latest_posts:
            return False
        newest_post = sorted(self.latest_posts, key=lambda post: post.date, reverse=True)[0]
        latest_age = now - newest_post.date
        return latest_age < age
    
    def missing_values(self) -> bool:
        if self.exists_in_telegram is None:
            return True
        if self.exists_in_telegram is False:
            return False
        return self.subscribers is None or self.latest_posts is None


class Searcher:
    def __init__(self, channels: List[Channel], animals: Dict[str, List[str]], ignored: List[Ignore]):
        self.channels = channels
        self.animals = animals
        self.ignored = ignored
        self.cache = {}
        self.unknown_expiry = datetime.timedelta(weeks=1)
        self.known_expiry = datetime.timedelta(weeks=5)
        self.post_age_cutoff = datetime.timedelta(days=365)

    def all_animal_names(self) -> List[str]:
        return list(itertools.chain(*self.animals.values()))

    def all_handle_patterns(self) -> List[str]:
        handle_patterns = set()
        for channel in self.channels:
            if channel.handle_pattern == "-":
                continue
            handle_patterns.add(channel.handle_pattern)
        return list(handle_patterns)

    def all_known_handles(self) -> List[str]:
        return [c.handle.lower() for c in self.channels]

    def total_handles(self) -> int:
        return len(self.cache)

    def unchecked_handles(self) -> int:
        return len([entry for entry in self.cache.values() if entry.exists_in_telegram is None])

    def ignored_dict(self) -> Dict[str, Ignore]:
        return {i.handle.lower(): i for i in self.ignored}

    def initialise_cache(self) -> None:
        self.load_cache_from_json()
        known_handles = self.all_known_handles()
        ignored_dict = self.ignored_dict()
        for animal_name in self.all_animal_names():
            for handle_pattern in self.all_handle_patterns():
                handle = handle_pattern.replace("?", animal_name).lower()
                if handle not in self.cache:
                    self.cache[handle] = SearchCacheEntry(
                        handle,
                        handle in known_handles,
                        None,
                        handle in ignored_dict,
                        None,
                        None,
                        None
                    )
                else:
                    self.cache[handle].in_store = handle in known_handles
                    self.cache[handle].ignored = handle in ignored_dict and not ignored_dict[handle].is_expired

    def save_cache_to_json(self) -> None:
        data = {
            "cache": {
                entry.handle: entry.to_json() for entry in self.cache.values()
            }
        }
        with open("cache/telegram_search_cache.json", "w") as f:
            json.dump(data, f, indent=2)

    def load_cache_from_json(self) -> None:
        try:
            with open("cache/telegram_search_cache.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        self.cache = {handle: SearchCacheEntry.from_json(entry_data) for handle, entry_data in
                      data.get("cache", {}).items()}

    def list_cache_entries_needing_update(self) -> List[SearchCacheEntry]:
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        # Remove ignored entries
        entries = [entry for entry in self.cache.values() if not entry.ignored]
        # Split by whether they have been checked
        unchecked, checked = split_list(
            entries,
            lambda entry: entry.missing_values()
        )
        # Split unchecked by whether they are known
        known_unchecked, unknown_unchecked = split_list(unchecked, lambda entry: entry.is_known)
        # Split checked by whether they are known
        known_checked, unknown_checked = split_list(checked, lambda entry: entry.is_known)
        # Build results list
        results = []
        # Unchecked known entries first, then unknown
        results += known_unchecked
        results += unknown_unchecked
        # Then unknown entries which are over expiry limit
        results += [entry for entry in unknown_checked if entry.older_than(self.unknown_expiry, now)]
        # Then known, ignored entries which are over expiry limit
        results += [entry for entry in known_checked if entry.older_than(self.known_expiry, now)]
        return results

    def check_channels(self) -> None:
        needs_update = self.list_cache_entries_needing_update()
        print(f"Looks like {len(needs_update)} handles need checking")
        for entry in needs_update:
            print(f"Checking whether @{entry.handle} exists on telegram")
            try:
                expired = entry.older_than(self.known_expiry if entry.is_known else self.unknown_expiry)
                if entry.exists_in_telegram is None or expired:
                    entry.check_existence()
                if entry.exists_in_telegram:
                    if entry.subscribers is None or expired:
                        entry.check_subscribers()
                    if entry.latest_posts is None or expired:
                        entry.check_posts()
                print(f"It {'exists' if entry.exists_in_telegram else 'does not exist'}")
                if entry.exists_in_telegram and entry.has_post_newer_than(self.post_age_cutoff):
                    print(f"And it is active, with {entry.subscribers} subscribers!")
            except Exception as e:
                print(f"{entry.handle} could not be cached: {e}")

    def list_alerts(self) -> List[str]:
        exists_unknown = [
            entry
            for entry in self.cache.values()
            if entry.exists_in_telegram and not entry.is_known and entry.has_post_newer_than(self.post_age_cutoff)
        ]
        ignored_missing = [
            entry for entry in self.cache.values() if entry.ignored and entry.exists_in_telegram is False
        ]
        ignored_expired = [
            i for i in self.ignored if i.is_expired
        ]
        stored_missing = [
            entry for entry in self.cache.values() if entry.in_store and entry.exists_in_telegram is False
        ]
        alerts = [
            f"These ({len(exists_unknown)}) active channels have been discovered:\n" +
            "\n".join(f"@{entry.handle}" for entry in exists_unknown),
            f"These ({len(ignored_missing)}) channels are ignored, but do not exist:\n" +
            "\n".join(f"@{entry.handle}" for entry in ignored_missing),
            f"These ({len(ignored_expired)}) channels were ignored, but have expired:\n" +
            "\n".join(f"@{ignore.handle}" for ignore in ignored_expired),
            f"These ({len(stored_missing)}) channels are in store, but do not exist:\n" +
            "\n".join(f"@{entry.handle}" for entry in stored_missing)
        ]
        return alerts


def setup_parser(subparsers: SubParserAdder) -> None:
    parser = subparsers.add_parser(
        "search_handles",
        description="Search for new channels, based on animal names and handle patterns",
        help="Search for new channels, based on animal names and handle patterns.\n"
             "Saves channel cache information to cache/telegram_search_cache.json",
        aliases=["find_channels", "hunt_channels"]
    )
    parser.set_defaults(func=do_search)


def do_search(args: Namespace) -> None:
    datastore = Datastore()
    # Load channels, animals, and ignore list
    a_channels = datastore.telegram_channels
    a_ignored = datastore.telegram_ignored
    # Create searcher
    searcher = Searcher(a_channels, datastore.animal_data, a_ignored)
    # Print some stats
    print(
        f"There are {len(searcher.all_animal_names())} animal names, {len(a_channels)} known telegram channels, "
        f"{len(a_ignored)} ignored telegram channels, and {len(searcher.all_handle_patterns())} handle patterns."
    )
    # Initialise searcher cache
    searcher.initialise_cache()
    # Print more stats
    print(
        f"There are {searcher.total_handles()} possible handles in total, of which, "
        f"{searcher.unchecked_handles()} have not been checked."
    )
    # Check channels
    searcher.check_channels()
    # Get alerts
    a_alerts = searcher.list_alerts()
    # Just print alerts for now. TODO
    for alert in a_alerts:
        print(alert)
    # Save cache
    searcher.save_cache_to_json()


if __name__ == "__main__":
    do_search(Namespace())
