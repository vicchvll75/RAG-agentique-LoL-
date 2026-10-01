"""Data Dragon : fichiers statiques officiels de Riot (noms et icones des champions, objets)."""

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


def champions() -> dict[int, dict]:
    """Identifiant numerique du champion vers {"name", "icon"} (ex. 62 vers Wukong)."""
    version = latest_version()
    return {
        int(c["key"]): {
            "name": c["name"],
            "icon": f"{DDRAGON}/cdn/{version}/img/champion/{c['image']['full']}",
        }
        for c in _data("champion").values()
    }


def item_names() -> dict[int, str]:
    return {int(item_id): item["name"] for item_id, item in _data("item").items()}


def profile_icon_url(icon_id: int) -> str:
    return f"{DDRAGON}/cdn/{latest_version()}/img/profileicon/{icon_id}.png"
