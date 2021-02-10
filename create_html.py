from dataclasses import dataclass
from typing import List, Callable, Any
import json

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


def load_channels() -> List[Channel]:
    with open("channels.json", "r") as f:
        channel_data_store = json.load(f)
    return [
        Channel.from_json(channel_data)
        for channel_data in channel_data_store["channels"]
    ]


def build_table(channels: List[Channel], tag, text, line):
    with tag("table"):
        with tag("thead"):
            with tag("tr"):
                line("th", "Link")
                line("th", "Animal")
                line("th", "Owner")
                line("th", "Notes")
        with tag("tbody"):
            for channel in channels:
                with tag("tr"):
                    with tag("td"):
                        with tag("a", href=f"https://t.me/{channel.handle}"):
                            text(f"@{channel.handle}")
                    line("td", channel.animal)
                    line("td", channel.owner)
                    line("td", channel.notes)


def create_doc(table_builder: Callable[[Any, Any, Any], None]):
    doc, tag, text, line = Doc().ttl()

    with tag("html"):
        with tag("body"):
            with tag("h1"):
                text("Telegram animal channels")
            with tag("p"):
                text("This site is just a list of telegram channels for pictures, gifs, and videos of animals")
            table_builder(tag, text, line)
    return indent(doc.getvalue())


if __name__ == "__main__":
    channel_list = load_channels()
    table = lambda x, y, z: build_table(channel_list, x, y, z)
    html = create_doc(table)
    with open("index.html", "w") as w:
        w.write(html)
