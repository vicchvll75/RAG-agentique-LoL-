"""Outil appele par le LLM : recupere les dernieres games d'un joueur et calcule ses stats."""

import re

from src import ddragon, riot_api, stats
from src.config import DEFAULT_GAMES, DEFAULT_REGION, MAX_GAMES, REGIONS

# Riot ID : nom de 3 a 16 caracteres, puis # et un tag de 2 a 5 caracteres alphanumeriques.
RIOT_ID_RE = re.compile(r"^\s*(.{3,16}?)\s*#\s*([A-Za-z0-9]{2,5})\s*$")
# On lit au plus ce nombre d'ids pour trouver assez de games sur la Faille (ARAM ignore).
MAX_IDS_SCANNED = 30


class ToolError(Exception):
    """Erreur a afficher telle quelle, sans repasser par le LLM (economise le quota Mistral)."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def parse_riot_id(raw: str) -> tuple[str, str]:
    match = RIOT_ID_RE.match(raw or "")
    if not match:
        raise ToolError(
            f"\"{raw}\" c'est pas un Riot ID complet frérot. Il me faut le format "
            "Pseudo#TAG (genre Faker#KR1), je vais pas deviner qui tu veux humilier."
        )
    return match.group(1), match.group(2)


def get_player_games(riot_id: str, count: int = DEFAULT_GAMES, region: str = DEFAULT_REGION) -> dict:
    """Renvoie {"pour_le_llm": resume chiffre, "affichage": donnees pour l'interface}."""
    game_name, tag_line = parse_riot_id(riot_id)
    count = max(1, min(int(count or DEFAULT_GAMES), MAX_GAMES))
    region = (region or DEFAULT_REGION).upper()
    if region not in REGIONS:
        region = DEFAULT_REGION

    try:
        account = riot_api.get_account(game_name, tag_line, region)
    except riot_api.RiotNotFound:
        raise ToolError(
            f"{game_name}#{tag_line} existe pas sur {region}. Vérifie le pseudo et le tag, "
            "ou alors même Riot a honte de lui."
        )
    puuid = account["puuid"]
    player = f"{account.get('gameName', game_name)}#{account.get('tagLine', tag_line)}"

    champions = ddragon.champions()
    items = ddragon.item_names()

    games = []
    match_ids = riot_api.get_match_ids(puuid, region, min(MAX_IDS_SCANNED, count * 3))
    for match_id in match_ids:
        game = stats.match_stats(riot_api.get_match(match_id, region), puuid, champions, items)
        if game:
            games.append(game)
        if len(games) == count:
            break

    if not games:
        raise ToolError(
            f"{player} a aucune game récente sur la Faille. Soit il a désinstallé, "
            "soit il joue qu'en ARAM. Dans les deux cas c'est suspect."
        )

    wins = sum(g["resultat"] == "VICTOIRE" for g in games)
    ranked = stats.ranked_summary(riot_api.get_ranked_entries(puuid, region))
    summary = {
        "joueur": player,
        "region": region,
        "classement": ranked,
        "bilan_sur_ces_games": f"{wins} victoire(s), {len(games) - wins} defaite(s) sur {len(games)}",
        "games_du_plus_recent_au_plus_ancien": games,
    }
    if len(games) < count:
        summary["note"] = f"Seulement {len(games)} game(s) sur la Faille trouvee(s) recemment."

    display = {"joueur": player, "region": region, "classement": ranked, "games": games}
    try:
        summoner = riot_api.get_summoner(puuid, region)
        display["niveau"] = summoner.get("summonerLevel")
        display["icone"] = ddragon.profile_icon_url(summoner["profileIconId"])
    except (riot_api.RiotError, KeyError):
        pass  # Purement decoratif : on s'en passe si Riot ne repond pas.

    return {"pour_le_llm": stats.for_llm(summary), "affichage": display}


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_player_games",
            "description": (
                "Recupere les dernieres parties League of Legends d'un joueur (Faille de "
                "l'invocateur) avec ses stats reelles, pour le roaster."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "riot_id": {
                        "type": "string",
                        "description": "Riot ID exact au format NomDeJeu#TAG, recopie tel quel.",
                    },
                    "count": {
                        "type": "integer",
                        "description": f"Nombre de games, {DEFAULT_GAMES} par defaut, {MAX_GAMES} maximum.",
                    },
                    "region": {
                        "type": "string",
                        "enum": list(REGIONS),
                        "description": f"Serveur, {DEFAULT_REGION} par defaut.",
                    },
                },
                "required": ["riot_id"],
            },
        },
    }
]
