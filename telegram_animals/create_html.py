from argparse import Namespace
from datetime import datetime, timedelta
from typing import List, TypeVar, Union, Generic, Tuple
import os

import pytz
from yattag import Doc, indent

from telegram_animals.data import Channel, load_channels_and_bots, load_channel_cache
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

    def get_colour_for_value(self, value: T):
        ratio = (value-self.start_value) / (self.end_value-self.start_value)
        ratio = max(0, min(1, ratio))
        colour = (
                self.start_colour[0] + ratio * (self.end_colour[0] - self.start_colour[0]),
                self.start_colour[1] + ratio * (self.end_colour[1] - self.start_colour[1]),
                self.start_colour[2] + ratio * (self.end_colour[2] - self.start_colour[2])
        )
        return f"rgb({colour[0]}, {colour[1]}, {colour[2]})"

    def style_for_value(self, value: T):
        colour = self.get_colour_for_value(value)
        return f"background-color: {colour};"


def build_channel_table(entities: List[Channel], doc):
    channel_cache = load_channel_cache()
    doc, tag, text, line = doc.ttl()
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    old = now - timedelta(days=180)
    date_scale = ColourScale(now, old, ColourScale.WHITE, ColourScale.RED)
    count_scale = ColourScale(0, 1000, ColourScale.WHITE, ColourScale.GREEN)

    with tag("table"):
        with tag("thead"):
            with tag("tr"):
                line("th", "Link")
                line("th", "Animal")
                line("th", "Owner")
                line("th", "# pics")
                line("th", "# gifs")
                line("th", "# vids")
                with tag("th"):
                    line("abbr", "# subs", title="Subscribers")
                line("th", "Latest post")
                line("th", "Notes")
        with tag("tbody"):
            last_animal = None
            for entity in entities:
                row_class = ""
                if last_animal is not None and last_animal != entity.animal:
                    row_class = "new-animal"
                last_animal = entity.animal
                with tag("tr", klass=row_class):
                    with tag("td"):
                        with tag("a", href=f"https://t.me/{entity.handle}"):
                            text(f"@{entity.handle}")
                    line("td", entity.animal)
                    line("td", entity.owner)
                    cache = channel_cache.get(entity.handle.casefold())
                    if cache:
                        line("td", cache.pic_count, style=count_scale.style_for_value(cache.pic_count))
                        line("td", cache.gif_count, style=count_scale.style_for_value(cache.gif_count))
                        line("td", cache.video_count, style=count_scale.style_for_value(cache.video_count))
                        line("td", cache.subscribers, style=count_scale.style_for_value(cache.subscribers))
                        latest_str = cache.latest_post.strftime("%Y-%m-%d") if cache.latest_post else "-"
                        line("td", latest_str, style=date_scale.style_for_value(cache.latest_post))
                    else:
                        for _ in range(5):
                            line("td", "?")
                    line("td", entity.notes)


def build_bot_table(entities: List[Channel], doc):
    doc, tag, text, line = doc.ttl()

    with tag("table"):
        with tag("thead"):
            with tag("tr"):
                line("th", "Link")
                line("th", "Animal")
                line("th", "Owner")
                line("th", "Notes")
        with tag("tbody"):
            for entity in entities:
                with tag("tr"):
                    with tag("td"):
                        with tag("a", href=f"https://t.me/{entity.handle}"):
                            text(f"@{entity.handle}")
                    line("td", entity.animal)
                    line("td", entity.owner)
                    line("td", entity.notes)


def create_doc(channels: List[Channel], bots: List[Channel]):
    doc, tag, text, line = Doc().ttl()

    with tag("html"):
        with tag("head"):
            line("title", "Telegram animal channels")
            doc.stag("link", rel="stylesheet", href="style.css")
        with tag("body"):
            with tag("h1"):
                text("Telegram animal channels")
            with tag("p"):
                text("This site is just a list of telegram channels for pictures, gifs, and videos of animals")
            build_channel_table(channels, doc)
            with tag("p"):
                doc.text("And the table of bots is below")
            build_bot_table(bots, doc)
            doc.text("If you would like to request any changes, please file an issue on the ")
            with doc.tag("a", href="https://github.com/Deer-Spangle/telegram-animals/"):
                text("github repository")
            text(". (Pull requests are also welcome!)")
            # Some basic, privacy-focused analytics
            doc.stag("script", src="https://getinsights.io/js/insights.js")
            with doc.tag("script"):
                text("insights.init('lrFaPwGuDpIqLUXt');")
                text("insights.trackPages();")
    return indent(doc.getvalue())


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
    list_channels, list_bots = load_channels_and_bots()
    html = create_doc(list_channels, list_bots)
    os.makedirs("public", exist_ok=True)
    with open(args.filename, "w") as w:
        w.write(html)


if __name__ == "__main__":
    do_html(Namespace())
