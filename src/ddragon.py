"""Data Dragon : fichiers statiques officiels de Riot (noms des champions et objets en francais)."""

import requests

from src import cache

DDRAGON = "https://ddragon.leagueoflegends.com"
LANG = "fr_FR"
VERSION_TTL_S = 6 * 3600


def latest_version() -> str:
    cached = cache.read("ddragon/version", max_age_s=VERSION_TTL_S)
    if cached:
        return cached
    version = requests.get(f"{DDRAGON}/api/versions.json", timeout=10).json()[0]
    cache.write("ddragon/version", version)
    return version


def _data(kind: str) -> dict:
    version = latest_version()
    key = f"ddragon/{version}_{LANG}_{kind}"
    cached = cache.read(key)
    if cached:
        return cached
    url = f"{DDRAGON}/cdn/{version}/data/{LANG}/{kind}.json"
    data = requests.get(url, timeout=10).json()["data"]
    cache.write(key, data)
    return data


def champion_names() -> dict[int, str]:
    """Identifiant numerique du champion vers son nom affiche (ex. 62 vers Wukong)."""
    return {int(c["key"]): c["name"] for c in _data("champion").values()}


def item_names() -> dict[int, str]:
    return {int(item_id): item["name"] for item_id, item in _data("item").items()}
