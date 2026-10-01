"""Fixtures communes : un faux match Riot et des secrets factices (aucun appel reseau)."""

import pytest

PUUID = "puuid-moi"


def participant(puuid, team, position, champ_id, champ, win, k, d, a, cs, dmg, gold, vision, **extra):
    base = {
        "puuid": puuid, "teamId": team, "teamPosition": position, "championId": champ_id,
        "championName": champ, "win": win, "kills": k, "deaths": d, "assists": a,
        "totalMinionsKilled": cs, "neutralMinionsKilled": 0,
        "totalDamageDealtToChampions": dmg, "goldEarned": gold, "visionScore": vision,
        "champLevel": 14, "wardsPlaced": 5, "visionWardsBoughtInGame": 0,
        "totalTimeSpentDead": d * 30, "largestMultiKill": 1,
        **{f"item{i}": 0 for i in range(7)},
    }
    base.update(extra)
    return base


def make_match(match_id="EUW1_1", queue=420, duration=1800, win=False):
    me = participant(PUUID, 100, "MIDDLE", 7, "Leblanc", win, 2, 11, 3, 147, 9000, 8000, 12, item0=3020)
    allies = [
        participant(f"a{i}", 100, pos, 1, "Annie", win, 4, 4, 4, 150, 15000, 10000, 20)
        for i, pos in enumerate(["TOP", "JUNGLE", "BOTTOM", "UTILITY"])
    ]
    enemies = [
        participant(f"e{i}", 200, pos, 122, "Darius", not win, 6, 2, 5, 250, 21000, 12000, 25)
        for i, pos in enumerate(["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"])
    ]
    return {
        "metadata": {"matchId": match_id},
        "info": {
            "queueId": queue, "gameDuration": duration, "gameEndTimestamp": 1_790_000_000_000,
            "participants": [me, *allies, *enemies],
        },
    }


@pytest.fixture(autouse=True)
def fake_secrets(monkeypatch):
    values = {"RIOT_API_KEY": "test", "MISTRAL_API_KEY": "test"}

    def fake(name, default=None):
        return values.get(name, default)

    for module in ("src.riot_api", "src.agent"):
        monkeypatch.setattr(f"{module}.secret", fake)


@pytest.fixture
def no_ddragon(monkeypatch):
    monkeypatch.setattr("src.ddragon.champions", lambda: {7: {"name": "LeBlanc", "icon": "x"}, 122: {"name": "Darius", "icon": "y"}, 1: {"name": "Annie", "icon": "z"}})
    monkeypatch.setattr("src.ddragon.item_names", lambda: {3020: "Chaussures du sorcier"})
