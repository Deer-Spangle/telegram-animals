import argparse
from typing import Protocol, List


class SubParserAdder(Protocol):
    def add_parser(
            self,
            name: str,
            *,
            description: str = None,
            help: str = None,
            aliases: List[str] = None,
    ) -> argparse.ArgumentParser:
        ...
