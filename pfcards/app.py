from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import requests
import json
import logging

from .packs import load_packs

LOG = logging.getLogger(__name__)
PACKS = load_packs()

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

    cards = []

    basics_fields = ["name", "class", "dualClass", "level", "ancestry", "heritage", "background", "alignment", "gender", "age", "deity", "sizeName", "keyability", "languages", "resistances"]
    basics = {k: build[k] for k in basics_fields}
    basics["ac"] = build["acTotal"]["acTotal"]
    basics["speed"] = build["attributes"]["speed"]
    basics["type"] = "stats"
    cards.append(basics)

    for caster in build.get("spellCasters", []):
        for spells in caster["spells"]:
            level = spells["spellLevel"]
            for name in spells["list"]:
                cards.append({
                    **find_in_pack(name, ["spell"]),
                    **{
                        "tradition": caster["magicTradition"],
                        "ability": caster["ability"],
                        "class": caster["name"],
                    }
                })

    for tradition_name, tradition in build.get("focus", {}).items():
        for ability_name, ability in tradition.items():
            for name in ability.get("focusCantrips", []):
                cards.append(dict(
                    find_in_pack(name, ["spell"]),
                        tradition=tradition_name,
                        ability=ability_name,
                        spell_type="Focus Cantrip",
                    )
                )
            for name in ability.get("focusSpells", []):
                cards.append(dict(
                    find_in_pack(name, ["spell"]),
                        tradition=tradition_name,
                        ability=ability_name,
                        spell_type="Focus Spell",
                    )
                )

    for feat in build["feats"]:
        name = feat[0]
        cards.append(find_in_pack(feat[0], ["feat", "heritage"]))

    return JSONResponse(cards)

def json_url(_id):
    return f"https://pathbuilder2e.com/json.php?id={_id}"

def get_json(_id):
    rsp = requests.get(json_url(_id), headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"})
    rsp.raise_for_status()
    obj = rsp.json()
    if not obj.get("success", False):
        raise Exception(f"Request for ID {_id} failed:\n{obj}")
    if "build" not in obj:
        raise Exception(f"Response for ID {_id} did not contain a `build`")
    return obj["build"]

app.mount("/static", StaticFiles(directory="static"), name="static")