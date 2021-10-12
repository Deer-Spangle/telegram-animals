from argparse import Namespace
from typing import List, Dict

from data import Channel, load_entities, load_animals
from telegram_animals.subparser import SubParserAdder


class DataException(Exception):
    pass


def validate_entity(entity: Channel, animal_data: Dict[str, List[str]]):
    if len(entity.animal) == 1:
        return
    if entity.animal not in animal_data:
        raise DataException(f"Animal missing from animal data: {entity.animal}")
    if entity.handle_pattern == "-":
        return
    names = animal_data[entity.animal]
    found_handle = False
    for name in names:
        possible_handle = entity.handle_pattern.replace("?", name)
        if possible_handle.casefold() == entity.handle.casefold():
            found_handle = True
    if not found_handle:
        raise DataException(f"Entity @{entity.handle} seems to use unlisted animal name for {entity.animal}")


def validate_animal(key, name_list):
    if key.lower().replace(" ", "") not in name_list:
        raise DataException(f"Animal key not in name list: {key}")
    for name in name_list:
        if " " in name:
            raise DataException(f"Spaces are not allowed in animal name: {name}")


def validate(entities: List[Channel], animal_data: Dict[str, List[str]]) -> List[DataException]:
    exceptions = []
    for entity in entities:
        try:
            validate_entity(entity, animal_data)
        except DataException as e:
            exceptions.append(e)
    for key, name_list in animal_data.items():
        try:
            validate_animal(key, name_list)
        except DataException as e:
            exceptions.append(e)
    return exceptions


def setup_subparser(subparsers: SubParserAdder) -> None:
    parser = subparsers.add_parser(
        "validate",
        description="Validates the data",
        help="Validates the data"
    )
    parser.set_defaults(func=do_validation)


def do_validation(args: Namespace):
    exc_list = validate(load_entities(), load_animals())
    if exc_list:
        raise DataException("Data failed to validate:\n" + "\n".join(str(e) for e in exc_list))


if __name__ == "__main__":
    do_validation(Namespace())
