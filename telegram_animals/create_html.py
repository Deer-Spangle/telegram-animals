import json
from argparse import Namespace
from datetime import datetime, timedelta
from typing import TypeVar, Union, Generic, Tuple
import os

import pytz
from jinja2 import Environment, PackageLoader, select_autoescape

from telegram_animals.data import Datastore
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
            channel.to_javascript_data(datastore) for channel in channels
        ]
    }
    return f"const telegramChannels = {json.dumps(data, indent=2)}"


def create_doc(datastore: Datastore) -> str:
    channels = datastore.all_channels
    bots = datastore.telegram_bots
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
        animals=sorted(datastore.list_animals),
        datastore=datastore,
        count_scale=count_scale,
        date_scale=date_scale
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
    with open("public/data.js", "w") as w:
        w.write(create_data_file(datastore))
    html = create_doc(datastore)
    with open(args.filename, "w") as w:
        w.write(html)


if __name__ == "__main__":
    do_html(Namespace())
