from typing import List
import os

from yattag import Doc, indent

from data import Channel, load_channels_and_bots, load_channel_cache


def build_channel_table(entities: List[Channel], doc):
    channel_cache = load_channel_cache()
    doc, tag, text, line = doc.ttl()

    with tag("table"):
        with tag("thead"):
            with tag("tr"):
                line("th", "Link")
                line("th", "Animal")
                line("th", "Owner")
                line("th", "# pics")
                line("th", "# gifs")
                line("th", "# vids")
                line("th", "Latest post")
                line("th", "Notes")
        with tag("tbody"):
            for entity in entities:
                with tag("tr"):
                    with tag("td"):
                        with tag("a", href=f"https://t.me/{entity.handle}"):
                            text(f"@{entity.handle}")
                    line("td", entity.animal)
                    line("td", entity.owner)
                    cache = channel_cache.get(entity.handle.casefold())
                    if cache:
                        line("td", cache.pic_count)
                        line("td", cache.gif_count)
                        line("td", cache.video_count)
                        latest_str = cache.latest_post.strftime("%Y-%m-%d") if cache.latest_post else "-"
                        line("td", latest_str)
                    else:
                        for _ in range(4):
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
    return indent(doc.getvalue())


if __name__ == "__main__":
    list_channels, list_bots = load_channels_and_bots()
    html = create_doc(list_channels, list_bots)
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w") as w:
        w.write(html)
