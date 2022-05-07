from argparse import Namespace
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import pytz
import os
import time
import json

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest as ContactSearchRequest
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterGif, InputMessagesFilterVideo, Message, \
    InputPeerChannel

from telegram_animals.data import Channel, ChannelCache, Datastore
from telegram_animals.subparser import SubParserAdder


class MediaType(Enum):
    Image = InputMessagesFilterPhotos()
    Gif = InputMessagesFilterGif()
    Video = InputMessagesFilterVideo()


class CachedSearcher:
    def __init__(self):
        self.search_cache = {}

    async def search_name(self, client: TelegramClient, handle: str) -> InputPeerChannel:
        if handle.casefold() in self.search_cache:
            return self.search_cache[handle.casefold()]
        response = await client(ContactSearchRequest(q=handle, limit=3))
        time.sleep(3)
        for chat in response.chats:
            input_entity = InputPeerChannel(chat.id, chat.access_hash)
            if chat.username:
                self.search_cache[chat.username.casefold()] = input_entity
        if handle.casefold() in self.search_cache:
            return self.search_cache[handle.casefold()]

    @classmethod
    def load_from_json(cls) -> 'CachedSearcher':
        searcher = cls()
        try:
            with open("scrape_cache_search_cache.json", "r") as f:
                searcher.search_cache = {
                    key: InputPeerChannel(value["channel_id"], value["channel_hash"])
                    for key, value in json.load(f).items()
                }
        except FileNotFoundError:
            pass
        return searcher

    def save_to_json(self):
        with open("scrape_cache_search_cache.json", "w") as f:
            json.dump({
                key: {
                    "channel_id": value.channel_id,
                    "channel_hash": value.access_hash
                } for key, value in self.search_cache.items()
            }, f, indent=2)


async def count_media_type(client: TelegramClient, entity: InputPeerChannel, media_type: MediaType) -> int:
    results = await client(SearchRequest(
        entity,
        "",
        media_type.value,
        None, None, 0, 0, 0, 0, 0, 0
    ))
    return results.count


async def latest_message(client: TelegramClient, entity: InputPeerChannel) -> Optional[Message]:
    async for msg in client.iter_messages(entity, 1):
        return msg
    return None


async def get_input_entity(
        client: TelegramClient,
        channel: Channel,
        searcher: CachedSearcher,
        old_cache: Optional[ChannelCache]
) -> InputPeerChannel:
    if old_cache and old_cache.channel_id:
        return InputPeerChannel(old_cache.channel_id, old_cache.channel_hash)
    try:
        entity = await client.get_input_entity(channel.handle)
        time.sleep(3)
        return entity
    except FloodWaitError as e:
        input_entity = await searcher.search_name(client, channel.handle)
        if not input_entity:
            raise Exception(f"Could not find in search. Entity lookup gave: {e}")
    return input_entity


async def generate_cache(
        client: TelegramClient,
        channel: Channel,
        searcher: CachedSearcher,
        old_cache: Optional[ChannelCache]
) -> ChannelCache:
    input_entity = await get_input_entity(client, channel, searcher, old_cache)
    images = await count_media_type(client, input_entity, MediaType.Image)
    gifs = await count_media_type(client, input_entity, MediaType.Gif)
    videos = await count_media_type(client, input_entity, MediaType.Video)
    entity = await client.get_entity(input_entity)
    title = entity.title
    full_entity = await client(GetFullChannelRequest(channel=input_entity))
    sub_count = full_entity.full_chat.participants_count
    bio = full_entity.full_chat.about
    latest_msg = await latest_message(client, input_entity)
    latest_post = None
    if latest_msg:
        latest_post = latest_msg.date
    return ChannelCache(
        datetime.utcnow().replace(tzinfo=pytz.utc),
        input_entity.channel_id,
        input_entity.access_hash,
        gifs,
        images,
        videos,
        sub_count,
        latest_post,
        bio,
        title
    )


async def generate_all_caches(client: TelegramClient, datastore: Datastore):
    channels = datastore.telegram_channels
    cache = datastore.telegram_cache
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    wait_before_refresh = timedelta(hours=6)
    searcher = CachedSearcher.load_from_json()
    for channel in channels:
        old_channel_cache = cache.get(channel.handle.casefold())
        if old_channel_cache:
            time_since_cache = now - old_channel_cache.date_checked
            if time_since_cache < wait_before_refresh:
                print(f"{channel.handle} was cached recently ({time_since_cache}), skipping.")
                continue
        try:
            channel_cache = await generate_cache(client, channel, searcher, old_channel_cache)
            datastore.telegram_cache[channel.handle.casefold()] = channel_cache
            datastore.save_telegram_cache()
            print(f"{channel.handle} cache updated.")
        except Exception as e:
            print(f"{channel.handle} could not be cached: {e}")
    datastore.save_telegram_cache()
    searcher.save_to_json()


def setup_parser(subparsers: SubParserAdder) -> None:
    parser = subparsers.add_parser(
        "scrape_cache",
        description="Scrapes the known channel list and updates cached values for dates, message counts, etc.",
        help="Scrapes the known channel list and updates cached values for dates, message counts, etc.\n"
             "Saves the data to cache/channel_cache.json",
        aliases=["update_cache"]
    )
    parser.set_defaults(func=do_scrape)
    parser.add_argument("--api_id", type=int, default=os.getenv("API_ID"))
    parser.add_argument("--api_hash", default=os.getenv("API_HASH"))
    parser.add_argument("--session_string", default=os.getenv("SESSION_STRING"))


def do_scrape(args: Namespace) -> None:
    datastore = Datastore()
    api_id = int(args.api_id)
    api_hash = args.api_hash
    session_string = args.session_string
    if session_string:
        session_arg = StringSession(session_string)
    else:
        session_arg = "telegram-animals"
    c = TelegramClient(session_arg, api_id, api_hash)
    c.start()
    c.loop.run_until_complete(generate_all_caches(c, datastore))


if __name__ == "__main__":
    do_scrape(Namespace())
