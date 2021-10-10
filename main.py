import argparse

from telegram_animals.validate import do_validation

parser = argparse.ArgumentParser(description="Entrypoint for the telegram animals scripts")
parser.add_argument(
    "--validate",
    help="Validates the stored data.",
    action="store_true",
)


if __name__ == "__main__":
    args = parser.parse_args()
    if args.validate:
        do_validation()
        print("Validation complete")
    else:
        print("Please specify a valid command")
