from datetime import datetime
from typing import List, Optional
from enum import Enum
import pytz
import os

from telethon import TelegramClient
from telethon.hints import Entity
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterGif, InputMessagesFilterVideo, Message

from data import load_channels, Channel, ChannelCache, save_channel_cache


class MediaType(Enum):
    Image = InputMessagesFilterPhotos()
    Gif = InputMessagesFilterGif()
    Video = InputMessagesFilterVideo()


async def count_media_type(client: TelegramClient, entity: Entity, media_type: MediaType) -> int:
    results = await client(SearchRequest(
        entity,
        "",
        media_type.value,
        None, None, 0, 0, 0, 0, 0, 0
    ))
    return results.count


async def latest_message(client: TelegramClient, entity: Entity) -> Optional[Message]:
    async for msg in client.iter_messages(entity, 1):
        return msg
    return None


async def generate_cache(client: TelegramClient, channel: Channel):
    entity = await client.get_entity(channel.handle)
    images = await count_media_type(client, entity, MediaType.Image)
    gifs = await count_media_type(client, entity, MediaType.Gif)
    videos = await count_media_type(client, entity, MediaType.Video)
    full_entity = await client(GetFullChannelRequest(channel=entity))
    sub_count = full_entity.full_chat.participants_count
    latest_msg = await latest_message(client, entity)
    latest_post = None
    if latest_msg:
        latest_post = latest_msg.date
    return ChannelCache(
        datetime.utcnow().replace(tzinfo=pytz.utc),
        gifs,
        images,
        videos,
        sub_count,
        latest_post
    )


async def generate_all_caches(client: TelegramClient, channels: List[Channel]):
    cache = {}
    for channel in channels:
        channel_cache = await generate_cache(client, channel)
        cache[channel] = channel_cache
    save_channel_cache(cache)


if __name__ == "__main__":
    channel_list = load_channels()[:5]
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    session_string = os.getenv("SESSION_STRING")
    c = TelegramClient(StringSession(session_string), api_id, api_hash)
    c.start()
    c.loop.run_until_complete(generate_all_caches(c, channel_list))
