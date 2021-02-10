from dataclasses import dataclass
from typing import List, Callable, Any, Tuple
import json
import os

from yattag import Doc, indent


@dataclass
class Channel:
    handle: str
    animal: str
    owner: str
    notes: str
    handle_pattern: str

    @classmethod
    def from_json(cls, data) -> 'Channel':
        return cls(
            data["handle"],
            data["animal"],
            data["owner"],
            data["notes"],
            data["handle_pattern"]
        )

    @property
    def is_bot(self) -> bool:
        return self.handle.lower().endswith("bot")


def load_entities() -> Tuple[List[Channel], List[Channel]]:
    with open("channels.json", "r") as f:
        data_store = json.load(f)
    sorted_entites = sorted([
        Channel.from_json(channel_data)
        for channel_data in data_store["channels"]
    ], key=lambda c: (c.animal, c.handle))
    return (
        [channel for channel in sorted_entites if not channel.is_bot],
        [bot for bot in sorted_entites if bot.is_bot]
    )


def build_table(entities: List[Channel], doc):
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
            build_table(channels, doc)
            with tag("p"):
                doc.text("And the table of bots is below")
            build_table(bots, doc)
            doc.text("If you would like to request any changes, please file an issue on the ")
            with doc.tag("a", href="https://github.com/Deer-Spangle/telegram-animals/"):
                text("github repository")
            text(". (Pull requests are also welcome!)")
    return indent(doc.getvalue())


if __name__ == "__main__":
    list_channels, list_bots = load_entities()
    html = create_doc(list_channels, list_bots)
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w") as w:
        w.write(html)
