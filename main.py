import argparse

from telegram_animals import create_html, scrape_cache, validate

parser = argparse.ArgumentParser(
    description="Entrypoint for the telegram animals scripts"
)
subparsers = parser.add_subparsers(
    title="Subcommands",
    description="Valid telegram-animals subcommands",
    required=True,
    dest="cmd"
)
validate.setup_subparser(subparsers)
create_html.setup_parser(subparsers)
scrape_cache.setup_parser(subparsers)


if __name__ == "__main__":
    args = parser.parse_args()
    args.func(args)
