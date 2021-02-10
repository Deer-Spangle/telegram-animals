import json
import pathlib

if __name__ == "__main__":
    tsv_file = pathlib.Path(__file__).parent.parent / "spreadsheet.tsv"
    json_file = pathlib.Path(__file__).parent.parent / "channels.json"
    channels = []
    with open(tsv_file, "r") as f:
        for line in f.readlines():
            if line.startswith("Notes") or not line:
                continue
            notes, animal, handle, pattern, owner = line.split("\t")
            channel = {
                "handle": handle,
                "owner": owner,
                "animal": animal,
                "notes": notes,
                "handle_pattern": pattern
            }
            channels.append(channel)
    output = {
        "channels": channels
    }
    with open(json_file, "w+") as f:
        json.dump(output, f, indent=2)
