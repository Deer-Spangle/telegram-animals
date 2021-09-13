import itertools
from dataclasses import dataclass
from typing import Optional, Dict, List
import datetime

from dateutil import parser

from data import Channel, load_entities, load_animals


@dataclass
class SearchCacheEntry:
    handle: str
    in_store: bool
    exists_in_telegram: Optional[bool]
    ignored: bool
    last_checked: datetime.datetime
    
    def to_json(self) -> Dict:
        return {
            "handle": self.handle,
            "in_store": self.in_store,
            "exists_in_telegram": self.exists_in_telegram,
            "ignored": self.ignored,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None
        }
    
    @classmethod
    def from_json(cls, data: Dict) -> 'SearchCacheEntry':
        return cls(
            data["handle"],
            data["in_store"],
            data["exists_in_telegram"],
            data["ignored"],
            parser.parse(data["last_checked"]) if data["last_checked"] else None
        )


class Searcher:
    def __init__(self, entites: List[Channel], animals: Dict[str, List[str]], ignored: List[str]):
        self.entites = entities
        self.animals = animals
        self.ignored = ignored
        self.cache = {}
    
    def all_animal_names(self) -> List[str]:
        return list(itertools.chain(*self.animals.values()))
    
    def all_handle_patterns(self) -> List[str]:
        handle_patterns = set()
        for entity in entities:
            if entity.handle_pattern == "-":
                continue
            handle_patterns.add(entity.handle_pattern)
        return list(handle_patterns)
    
    def all_known_handles(self) -> List[str]:
        return [e.handle for e in self.entities]
    
    def total_handles(self) -> int:
        return len(self.cache)
    
    def unchecked_handles(self) -> int:
        return len([entry for entry in self.cache.values() if entry.exists_in_telegram is None])
    
    def initialise_cache(self) -> None:
        self.load_cache_from_json()
        known_handles = self.all_known_handles()
        for animal_name in self.all_animal_names():
            for handle_pattern in self.all_handle_patterns():
                handle = handle_pattern.replace("?", animal_name)
                if handle not in self.cache:
                    self.cache[handle] = SearchCacheEntry(
                        handle, 
                        handle in known_handles,
                        None,
                        handle in self.ignored,
                        None
                    )
                else:
                    self.cache[handle].in_store = handle in known_handles
                    self.cache[handle].ignored = handle in self.ignored

    def save_cache_to_json(self):
        data = {
            "cache": {
                entry.handle: entry.to_json() for entry in self.cache.values()
            }
        }
        with open("cache/search_cache.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def load_cache_from_json(self):
        with open("cache/search_cache.json", "r") as f:
            data = json.load(f)
        self.cache = {handle: SearchCacheEntry.from_json(entry_data) for handle, entry_data in data["cache"]}
    

if __name__ == "__main__":
    # Load entities, animals, and ignore list
    entities = load_entities()
    animals = load_animals()
    ignored = []  # TODO
    # Create searcher
    searcher = Searcher(entites, animals, ignored)
    # Get all animal names
    animal_names = searcher.all_animal_names()
    # Get all handle patterns
    handle_patterns = searcher.all_handle_patterns()
    # Print some stats
    print(f"There are {len(animal_names)} animal names, {len(entities)} known channels, {len(ignored)} ignored channels, and {len(handle_patterns)} handle patterns.")
    # Initialise searcher cache
    searcher.initialise_cache()
    # Print more stats
    print(f"There are {searcher.total_handles()} possible handles in total, of which, {searcher.unchecked_handles()} have not been checked.")
