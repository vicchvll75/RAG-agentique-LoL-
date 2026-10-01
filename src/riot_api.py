"""Client de l'API officielle Riot Games (account v1, match v5, league v4)."""

import time
from urllib.parse import quote

import requests

from src import cache
from src.config import REGIONS, secret

MAX_RETRIES = 3
# Au dela, on abandonne plutot que de bloquer l'interface.
MAX_WAIT_S = 15

SESSION = requests.Session()


class RiotError(Exception):
    """Erreur Riot, avec un message affichable dans l'appli."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class RiotAuthError(RiotError):
    pass


class RiotNotFound(RiotError):
    pass


class RiotRateLimited(RiotError):
    pass


class RiotMissingKey(RiotError):
    pass


def _get(url: str, params: dict | None = None):
    key = secret("RIOT_API_KEY")
    if not key:
        raise RiotMissingKey("RIOT_API_KEY manquante dans les secrets.")

    for attempt in range(MAX_RETRIES + 1):
        # La cle passe dans un header, jamais dans l'URL (qui peut finir dans des logs).
        response = SESSION.get(
            url, params=params, headers={"X-Riot-Token": key}, timeout=10
        )

        if response.status_code == 200:
            return response.json()
        if response.status_code in (401, 403):
            raise RiotAuthError(
                "Clé Riot invalide ou expirée (la clé de dev dure 24 h)."
            )
        if response.status_code == 404:
            raise RiotNotFound("Introuvable chez Riot.")
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", "2"))
            if wait > MAX_WAIT_S or attempt == MAX_RETRIES:
                raise RiotRateLimited("Limite de requêtes Riot atteinte.")
            time.sleep(wait)
            continue
        if response.status_code >= 500 and attempt < MAX_RETRIES:
            time.sleep(1 + attempt)
            continue
        raise RiotError(f"Erreur Riot inattendue ({response.status_code}).")

    raise RiotError("Riot ne répond pas.")


def _routes(region: str) -> tuple[str, str]:
    platform, regional = REGIONS[region]
    return (
        f"https://{platform}.api.riotgames.com",
        f"https://{regional}.api.riotgames.com",
    )


def get_account(game_name: str, tag_line: str, region: str) -> dict:
    _, regional = _routes(region)
    return _get(
        f"{regional}/riot/account/v1/accounts/by-riot-id/"
        f"{quote(game_name)}/{quote(tag_line)}"
    )


def get_match_ids(puuid: str, region: str, count: int) -> list[str]:
    _, regional = _routes(region)
    return _get(
        f"{regional}/lol/match/v5/matches/by-puuid/{puuid}/ids",
        params={"start": 0, "count": count},
    )


def get_match(match_id: str, region: str) -> dict:
    """Detail d'un match. Un match termine ne change jamais : cache disque sans expiration."""
    cached = cache.read(f"matches/{match_id}")
    if cached is not None:
        return cached
    _, regional = _routes(region)
    match = _get(f"{regional}/lol/match/v5/matches/{match_id}")
    cache.write(f"matches/{match_id}", match)
    return match


def get_ranked_entries(puuid: str, region: str) -> list[dict]:
    platform, _ = _routes(region)
    return _get(f"{platform}/lol/league/v4/entries/by-puuid/{puuid}")


def get_summoner(puuid: str, region: str) -> dict:
    platform, _ = _routes(region)
    return _get(f"{platform}/lol/summoner/v4/summoners/by-puuid/{puuid}")
