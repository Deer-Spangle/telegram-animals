import dataclasses
import json
import os
from argparse import Namespace
from datetime import datetime
from typing import List, Optional

import dateutil.parser
import twitter
from twitter import Status

from telegram_animals.data import Datastore, ChannelCache
from telegram_animals.subparser import SubParserAdder


def setup_parser(subparsers: SubParserAdder) -> None:
    try:
        with open("twitter_config.json") as f:
            twitter_conf = json.load(f)
    except FileNotFoundError:
        twitter_conf = {
            "api_key": os.getenv("API_KEY"),
            "api_key_secret": os.getenv("API_KEY_SECRET"),
            "access_token_key": os.getenv("ACCESS_TOKEN_KEY"),
            "access_token_secret": os.getenv("ACCESS_TOKEN_SECRET")
        }
    parser = subparsers.add_parser(
        "scrape_twitter",
        description="Scrapes the known twitter feeds and updates cached values for dates, message counts, etc.",
        help="Scrapes the known twitter feed list and updated the cached values for dates, message counts, etc.\n"
             "Saves the data to cache/twitter_cache.json",
        aliases=["update_twitter"]
    )
    parser.set_defaults(func=do_twitter_scrape)
    parser.add_argument("--api_key", default=twitter_conf["api_key"])
    parser.add_argument("--api_key_secret", default=twitter_conf["api_key_secret"])
    parser.add_argument("--access_token_key", default=twitter_conf["access_token_key"])
    parser.add_argument("--access_token_secret", default=twitter_conf["access_token_secret"])


@dataclasses.dataclass
class TwitterCache:
    handle: str
    user_id: int
    display_name: int
    bio: str
    user_location: str
    user_url: str
    creation_datetime: datetime
    num_subs: int
    num_tweets: int
    latest_post: datetime
    sample: "TwitterSample" = None

    @property
    def num_pics(self) -> Optional[int]:
        if self.sample is None:
            return None
        pics_per_tweet = self.sample.num_pics / self.sample.num_tweets
        return int(pics_per_tweet * self.num_tweets)

    @property
    def num_vids(self) -> Optional[int]:
        if self.sample is None:
            return None
        vids_per_tweet = self.sample.num_vids / self.sample.num_tweets
        return int(vids_per_tweet * self.num_tweets)

    @property
    def num_gifs(self) -> Optional[int]:
        if self.sample is None:
            return None
        gifs_per_tweet = self.sample.num_gifs / self.sample.num_tweets
        return int(gifs_per_tweet * self.num_tweets)


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
    num_vid_tweets: int = 0
    num_gif_tweets: int = 0
    num_other_media_tweets: int = 0
    num_no_media_tweets: int = 0

    def add_tweet(self, tweet: Status):
        self.num_tweets += 1
        tweet_datetime = dateutil.parser.parse(tweet.created_at)
        if self.latest_datetime is None or tweet_datetime > self.latest_datetime:
            self.latest_id = tweet.id
            self.latest_datetime = tweet_datetime
        if self.earliest_datetime is None or tweet_datetime < self.earliest_datetime:
            self.earliest_id = tweet.id
            self.earliest_datetime = tweet_datetime
        if not tweet.media:
            self.num_no_media_tweets += 1
            return
        media_types = [media.type for media in tweet.media]
        if all(m == "video" for m in media_types):
            self.num_vid_tweets += 1
        elif all(m == "photo" for m in media_types):
            self.num_pic_tweets += 1
        elif all(m == "animated_gif" for m in media_types):
            self.num_gif_tweets += 1
        else:
            self.num_other_media_tweets += 1
        for media_type in media_types:
            if media_type == "photo":
                self.num_pics += 1
            elif media_type == "video":
                self.num_vids += 1
            elif media_type == "animated_gif":
                self.num_gifs += 1
            else:
                self.num_other_media += 1


def fetch_new_tweets(api: twitter.Api, user_id: int, since_id: int, since_datetime: datetime) -> List[Status]:
    max_id = None
    new_tweets = []
    while True:
        timeline = api.GetUserTimeline(user_id=user_id, since_id=since_id, max_id=max_id)
        new_batch = []
        for tweet in timeline:
            tweet_datetime = dateutil.parser.parse(tweet.created_at)
            if tweet_datetime < since_datetime and tweet.id not in [t.id for t in new_tweets] + [newest_id]:
                new_tweets.append(tweet)
                new_batch.append(tweet)
            max_id = max(tweet.id, max_id)
        if not new_batch:
            break
    return new_tweets


def fetch_initial_tweets(api: twitter.Api, user_id: int) -> List[Status]:
    tweets = []
    max_id = None
    while True:
        timeline = api.GetUserTimeline(user_id=user_id, max_id=max_id)
        new_batch = []
        for tweet in timeline:
            if tweet.id not in [t.id for t in tweets]:
                tweets.append(tweet)
                new_batch.append(tweet)
            max_id = max(tweet.id, max_id)
        if not new_batch or len(tweets) > 1000:
            break
    return tweets


def do_twitter_scrape(ns: Namespace):
    api = twitter.Api(
        consumer_key=ns.api_key,
        consumer_secret=ns.api_key_secret,
        access_token_key=ns.access_token_key,
        access_token_secret=ns.access_token_secret
    )
    datastore = Datastore()
    for channel in datastore.twitter_feeds:
        user_cache = datastore.fetch_twitter_cache(channel.handle)
        if user_cache is None:
            user = api.GetUser(screen_name=channel.handle)
            user_cache = TwitterCache(
                channel.handle,
                user.id,
                user.name,
                user.description,
                user.location,
                user.url,
                dateutil.parser.parse(user.created_at),
                user.followers_count,
                user.statuses_count,
                dateutil.parser.parse(user.status.created_at)
            )
        else:
            user = api.GetUser(user_id=user_cache.user_id)
            user_cache
        if user_cache.sample is None:
            user_cache.sample = TwitterSample()
            tweets = fetch_initial_tweets(api, user.id)
        else:
            tweets = fetch_new_tweets(api, user.id, user_cache.sample.latest_id, user_cache.sample.latest_datetime)
        for tweet in tweets:
            user_cache.sample.add_tweet(tweet)
        print(
            f"{user_cache.handle}: {user_cache.num_tweets} tweets ({user_cache.sample.num_tweets} sampled), "
            f"{user_cache.num_subs} subscribers"
        )
    pass
