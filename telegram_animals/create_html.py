import json
from argparse import Namespace
from datetime import datetime, timedelta
from typing import TypeVar, Union, Generic, Tuple
import os

import pytz
from jinja2 import Environment, PackageLoader, select_autoescape

from telegram_animals.data.datastore import Datastore
from telegram_animals.subparser import SubParserAdder

T = TypeVar("T", bound=Union[float, datetime])
Colour = Tuple[float, float, float]


class ColourScale(Generic[T]):
    YELLOW = (255, 255, 0)
    GREEN = (87, 187, 138)
    RED = (230, 124, 115)
    WHITE = (255, 255, 255)

    def __init__(self, start_val: T, end_val: T, start_colour: Colour, end_colour: Colour):
        self.start_value = start_val
        self.end_value = end_val
        self.start_colour = start_colour
        self.end_colour = end_colour

    def get_colour_for_value(self, value: T) -> str:
        if value is None:
            value = min(self.start_value, self.end_value)
        ratio = (value-self.start_value) / (self.end_value-self.start_value)
        ratio = max(0, min(1, ratio))
        colour = (
                self.start_colour[0] + ratio * (self.end_colour[0] - self.start_colour[0]),
                self.start_colour[1] + ratio * (self.end_colour[1] - self.start_colour[1]),
                self.start_colour[2] + ratio * (self.end_colour[2] - self.start_colour[2])
        )
        return f"rgb({colour[0]:0.0f}, {colour[1]:0.0f}, {colour[2]:0.0f})"

    def style_for_value(self, value: T) -> str:
        colour = self.get_colour_for_value(value)
        return f"background-color: {colour};"


def create_data_file(datastore: Datastore) -> str:
    channels = datastore.all_channels
    data = {
        "channels": [
            channel.to_javascript_data(datastore.fetch_cache(channel.channel_type, channel.handle)) for channel in channels
        ]
    }
    return f"const telegramChannels = {json.dumps(data, indent=2)}"


def create_doc(datastore: Datastore) -> str:
    channels = sorted(datastore.all_channels, key=lambda c: (c.animal, c.handle.casefold()))
    bots = sorted(datastore.telegram_bots, key=lambda b: (b.animal, b.handle.casefold()))
    env = Environment(
        loader=PackageLoader("telegram_animals"),
        autoescape=select_autoescape()
    )
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    old = now - timedelta(days=180)
    date_scale = ColourScale(now, old, ColourScale.WHITE, ColourScale.RED)
    count_scale = ColourScale(0, 1000, ColourScale.WHITE, ColourScale.GREEN)

    template = env.get_template("index.html")
    return template.render(
        channels=channels,
        bots=bots,
        animals=sorted(datastore.list_animals_with_channels),
        datastore=datastore,
        count_scale=count_scale,
        date_scale=date_scale
    )


def create_error_file(datastore: Datastore) -> str:
    data = {
        "telegram_cache_errors": [
            err.to_json() for err in datastore._telegram_cache_errors
        ],
        "twitter_cache_errors": [
            err.to_json() for err in datastore._twitter_cache_errors
        ]
    }
    return f"const telegramChannels = {json.dumps(data, indent=2)}"


def create_error_report(datastore: Datastore) -> str:
    telegram_data_errors = datastore._telegram_cache_errors
    twitter_data_errors = datastore._twitter_cache_errors
    env = Environment(
        loader=PackageLoader("telegram_animals"),
        autoescape=select_autoescape()
    )
    template = env.get_template("errors.html")
    return template.render(
        telegram_errors=telegram_data_errors,
        twitter_errors=twitter_data_errors
    )


def setup_parser(subparsers: SubParserAdder) -> None:
    parser = subparsers.add_parser(
        "create_html",
        description="Generates and writes the HTML for the website",
        help="Generates the HTML for the website",
        aliases=["html"]
    )
    parser.set_defaults(func=do_html)
    parser.add_argument("--filename", "-f", default="public/index.html")


def do_html(args: Namespace):
    datastore = Datastore()
    os.makedirs("public", exist_ok=True)
    # Public site data
    with open("public/data.js", "w") as w:
        w.write(create_data_file(datastore))
    # Public site
    html = create_doc(datastore)
    with open(args.filename, "w") as w:
        w.write(html)
    # Error page data
    with open("public/errors.js", "w") as w:
        w.write(create_error_file(datastore))
    # Error page
    error_doc = create_error_report(datastore)
    with open("public/errors.html", "w") as w:
        w.write(create_error_report(datastore))


if __name__ == "__main__":
    do_html(Namespace())
