import json
from typing import List, Dict

from create_html import Channel


class DataException(Exception):
    pass


def load_entities() -> List[Channel]:
    with open("channels.json", "r") as f:
        entity_data = json.load(f)
    return [Channel.from_json(entity_datum) for entity_datum in entity_data["channels"]]


def load_animals() -> Dict[str, List[str]]:
    with open("animals.json", "r") as f:
        return json.load(f)


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


if __name__ == "__main__":
    entites = load_entities()
    animal_data = load_animals()
    exceptions = []
    for entity in entites:
        try:
            validate_entity(entity, animal_data)
        except DataException as e:
            exceptions.append(e)
    for key, name_list in animal_data.items():
        try:
            validate_animal(key, name_list)
        except DataException as e:
            exceptions.append(e)
    if exceptions:
        raise DataException("Data failed to validate:\n" + "\n".join(str(e) for e in exceptions))
