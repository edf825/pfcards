from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import markdown
import requests
import re
import json
import logging

# from .foundry import load_packs
from pfcards.aonprd import load_packs

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s",
)

LOG = logging.getLogger(__name__)
PACKS = load_packs()

DEBUG_JSON = None

app = FastAPI()

class CardsModel(BaseModel):
    id: int

@app.get("/")
def root():
    return FileResponse('static/index.html')

@app.post("/cards/")
def cards(cards_model: CardsModel):
    build = get_json(cards_model.id)

    def find_in_pack(name, subsets):
        for subset in subsets:
            if name in PACKS[subset]:
                return PACKS[subset][name]
        msg = f"Couldn't find {name} in {subsets}"
        LOG.warning(msg)
        return {"name": name, "type": "error", "message": msg}

    cards = {}

    basics_fields = ["name", "class", "dualClass", "level", "ancestry", "heritage", "background", "alignment", "gender", "age", "deity", "sizeName", "keyability", "languages", "resistances"]
    basics = {k: build[k] for k in basics_fields}
    basics["ac"] = build["acTotal"]["acTotal"]
    basics["speed"] = build["attributes"]["speed"]
    basics["type"] = "stats"
    cards["basics"] = basics

    for caster in build.get("spellCasters", []):
        for spells in caster["spells"]:
            level = spells["spellLevel"]
            for name in spells["list"]:
                cards[(name, "spell", caster["magicTradition"], caster["ability"], caster["name"])] = {
                    **find_in_pack(name, ["spell"]),
                    **{
                        "tradition": caster["magicTradition"],
                        "ability": caster["ability"],
                        "class": caster["name"],
                    }
                }

    for tradition_name, tradition in build.get("focus", {}).items():
        for ability_name, ability in tradition.items():
            for name in ability.get("focusCantrips", []):
                cards[(name, "focusCantrips", tradition_name, ability_name)] = dict(
                    find_in_pack(name, ["spell"]),
                    tradition=tradition_name,
                    ability=ability_name,
                    spell_type="Focus Cantrip",
                )
            for name in ability.get("focusSpells", []):
                cards[(name, "focusSpells", tradition_name, ability_name)] = dict(
                    find_in_pack(name, ["spell"]),
                    tradition=tradition_name,
                    ability=ability_name,
                    spell_type="Focus Spell",
                )

    for feat in build["feats"]:
        name = feat[0]
        desc = (feat + [None] * 5)[4]  # e.g. "Witch Feat 4", "Elf Feat 9"

        card = None
        if desc is not None:
            suffix = f" ({desc.split()[0]})"
            card = find_in_pack(feat[0] + suffix, ["feat", "heritage"])

        if card is None or card["type"] == "error":
            card = find_in_pack(feat[0], ["feat", "heritage"])

        cards[(name, "feats")] = card

    card_list = list(cards.values())
    for card in card_list:
        if "markdown" in card:
            card["parsed_markdown"] = markdown.markdown(
                re.sub(
                    "<([^/][^>]*)>",
                    '<\\1 markdown="1">', 
                    card["markdown"].replace("\r\n>", ">"),
                ),
                extensions=["md_in_html"],
            )

    return JSONResponse(card_list)

def json_url(_id):
    return f"https://pathbuilder2e.com/json.php?id={_id}"

def maybe_read_debug_json():
    if DEBUG_JSON is not None:
        with open(DEBUG_JSON) as fd:
            return json.load(fd)["build"]

def get_json(_id):
    debug = maybe_read_debug_json()
    if debug is not None:
        return debug

    rsp = requests.get(json_url(_id), headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"})
    rsp.raise_for_status()
    obj = rsp.json()
    if not obj.get("success", False):
        raise Exception(f"Request for ID {_id} failed:\n{obj}")
    if "build" not in obj:
        raise Exception(f"Response for ID {_id} did not contain a `build`")
    return obj["build"]

app.mount("/static", StaticFiles(directory="static"), name="static")