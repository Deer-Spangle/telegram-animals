import json
from dataclasses import dataclass
from typing import Tuple, List, Dict


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


def load_channels_and_bots() -> Tuple[List[Channel], List[Channel]]:
    with open("telegram.json", "r") as f:
        data_store = json.load(f)
    sorted_entites = sorted([
        Channel.from_json(channel_data)
        for channel_data in data_store["entities"]
    ], key=lambda c: (c.animal, c.handle))
    return (
        [channel for channel in sorted_entites if not channel.is_bot],
        [bot for bot in sorted_entites if bot.is_bot]
    )


def load_entities() -> List[Channel]:
    with open("telegram.json", "r") as f:
        telegram_data = json.load(f)
    return [Channel.from_json(entity_datum) for entity_datum in telegram_data["entities"]]


def load_animals() -> Dict[str, List[str]]:
    with open("animals.json", "r") as f:
        return json.load(f)
