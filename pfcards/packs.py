import glob
import json
import os

MODULE_DIR = os.path.dirname(__file__)
PACKS_DIR = os.path.join(MODULE_DIR, "../foundry-pf2e/packs/")
PACKS_DIR_OLD = os.path.join(MODULE_DIR, "../foundry-pf2e-old/packs/")

def load_packs():
    packs = {}

    files = (
        glob.glob(os.path.join(PACKS_DIR_OLD, "**", "*.json"), recursive=True)
        + glob.glob(os.path.join(PACKS_DIR, "**", "*.json"), recursive=True)
    )

    for file in files:
        if not file.endswith(".json"):
            continue

        with open(file) as fd:
            obj = json.load(fd)

            if "name" not in obj:
                continue

            if "type" not in obj:
                continue

            packs.setdefault(obj["type"], {})[obj["name"]] = obj
            packs[obj["type"]][os.path.basename(file).split(".")[0]] = obj

    return packs
