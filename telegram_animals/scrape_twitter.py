import json
import os
from argparse import Namespace
from datetime import datetime, timedelta
from typing import List, Optional
import time

import dateutil.parser
import twitter
from twitter import Status

from telegram_animals.data.cache import TwitterCache, TwitterSample
from telegram_animals.data.datastore import Datastore, Channel
from telegram_animals.subparser import SubParserAdder

WAIT_BEFORE_REFRESH = timedelta(hours=6)
INITIAL_TWEET_SAMPLE = 1000


def min_not_null(a: Optional[int], b: Optional[int]) -> Optional[int]:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


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


def add_tweet_to_sample(sample: TwitterSample, tweet: Status):
    sample.num_tweets += 1
    tweet_datetime = dateutil.parser.parse(tweet.created_at)
    if sample.latest_datetime is None or tweet_datetime > sample.latest_datetime:
        sample.latest_id = tweet.id
        sample.latest_datetime = tweet_datetime
    if sample.earliest_datetime is None or tweet_datetime < sample.earliest_datetime:
        sample.earliest_id = tweet.id
        sample.earliest_datetime = tweet_datetime
    if not tweet.media:
        sample.num_no_media_tweets += 1
        return
    media_types = [media.type for media in tweet.media]
    if all(m == "photo" for m in media_types):
        sample.num_pic_tweets += 1
    for media_type in media_types:
        if media_type == "photo":
            sample.num_pics += 1
        elif media_type == "video":
            sample.num_vids += 1
        elif media_type == "animated_gif":
            sample.num_gifs += 1
        else:
            sample.num_other_media += 1


def fetch_new_tweets(api: twitter.Api, user_id: int, since_id: int, since_datetime: datetime) -> List[Status]:
    max_id = None
    new_tweets = []
    while True:
        time.sleep(1)
        timeline = api.GetUserTimeline(user_id=user_id, since_id=since_id, max_id=max_id)
        new_batch = []
        for tweet in timeline:
            tweet_datetime = dateutil.parser.parse(tweet.created_at)
            if tweet_datetime < since_datetime and tweet.id not in [t.id for t in new_tweets] + [since_id]:
                new_tweets.append(tweet)
                new_batch.append(tweet)
            max_id = min_not_null(tweet.id, max_id)
        if not new_batch:
            break
    return new_tweets


def fetch_initial_tweets(api: twitter.Api, user_id: int) -> List[Status]:
    tweets = []
    max_id = None
    while True:
        time.sleep(1)
        timeline = api.GetUserTimeline(user_id=user_id, max_id=max_id)
        new_batch = []
        for tweet in timeline:
            if tweet.id not in [t.id for t in tweets]:
                tweets.append(tweet)
                new_batch.append(tweet)
            max_id = min_not_null(tweet.id, max_id)
        if not new_batch or len(tweets) > INITIAL_TWEET_SAMPLE:
            break
    return tweets


def create_twitter_cache(user: twitter.User) -> TwitterCache:
    latest_post_datetime = None
    if user.status:
        latest_post_datetime = dateutil.parser.parse(user.status.created_at)
    return TwitterCache(
        datetime.now(),
        user.id,
        user.name,
        user.description,
        user.location,
        user.url,
        dateutil.parser.parse(user.created_at),
        user.followers_count,
        user.statuses_count,
        latest_post_datetime
    )


def update_twitter_cache(twitter_cache: TwitterCache, user: twitter.User) -> None:
    twitter_cache._date_checked = datetime.now()
    twitter_cache.display_name = user.name
    twitter_cache.bio = user.description
    twitter_cache.user_location = user.location
    twitter_cache.user_url = user.url
    twitter_cache._subscribers = user.followers_count
    twitter_cache._post_count = user.statuses_count
    latest_post_datetime = None
    if user.status:
        latest_post_datetime = dateutil.parser.parse(user.status.created_at)
    twitter_cache._latest_post = latest_post_datetime


def update_twitter_sample(api: twitter.Api, user: twitter.User, user_cache: TwitterCache) -> None:
    if user_cache.sample.num_tweets == 0:
        print("Fetching initial tweet sample")
        tweets = fetch_initial_tweets(api, user.id)
    else:
        print("Updating tweet sample")
        tweets = fetch_new_tweets(api, user.id, user_cache.sample.latest_id, user_cache.sample.latest_datetime)
    for tweet in tweets:
        add_tweet_to_sample(user_cache.sample, tweet)


def update_cache_for_channel(api: twitter.Api, datastore: Datastore, channel: Channel) -> TwitterCache:
    user_cache = datastore.fetch_twitter_cache(channel.handle)
    if user_cache is None:
        print("Creating new twitter cache")
        time.sleep(2)
        user = api.GetUser(screen_name=channel.handle)
        user_cache = create_twitter_cache(user)
        update_twitter_sample(api, user, user_cache)
    if datetime.now() - user_cache.date_checked > WAIT_BEFORE_REFRESH:
        print("Updating twitter user cache")
        time.sleep(2)
        user = api.GetUser(user_id=user_cache.user_id)
        update_twitter_cache(user_cache, user)
        update_twitter_sample(api, user, user_cache)
    print(
        f"{channel.handle}: {user_cache.post_count} tweets ({user_cache.sample.num_tweets} sampled), "
        f"{user_cache.subscribers} subscribers"
    )
    return user_cache


def do_twitter_scrape(ns: Namespace):
    api = twitter.Api(
        consumer_key=ns.api_key,
        consumer_secret=ns.api_key_secret,
        access_token_key=ns.access_token_key,
        access_token_secret=ns.access_token_secret
    )
    datastore = Datastore()
    for channel in datastore.twitter_feeds:
        try:
            user_cache = update_cache_for_channel(api, datastore, channel)
            datastore.update_twitter_cache(channel.handle, user_cache)
            datastore.save_twitter_cache()
        except Exception as e:
            print(f"{channel.handle} could not be cached: {e}")
    datastore.save_telegram_cache()
