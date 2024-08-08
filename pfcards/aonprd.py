import json
import logging
import os
import requests

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

BASE_URL = "https://elasticsearch.aonprd.com/json-data/"
INDEX_URL = "aon39-index.json"

CACHE_DIR = "aon-cache"


def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)


def fetch_cached(path):
    LOG.info(f"fetching {path}")
    ensure_cache_dir()
    cache_path = os.path.join(CACHE_DIR, path)

    if not os.path.exists(cache_path):
        url = BASE_URL + path

        rsp = requests.get(url)
        try:
            rsp.raise_for_status()
        except:
            LOG.exception(f"request failed to {url}")
            raise

        with open(cache_path, "w") as fd:
            json.dump(rsp.json(), fd)

    with open(cache_path) as fd:
        return json.load(fd)


def load_packs():
    LOG.info("loading AON packs")
    result = {}
    index = fetch_cached(INDEX_URL)
    for key in index:
        chunk = fetch_cached(f"{key}.json")
        for item in chunk:
            result.setdefault(item["category"], {})[item["name"]] = item
            result[item["category"]][item["name"].lower()] = item
    return result


if __name__ == "__main__":
    load_packs()
