from src import stats
from tests.conftest import PUUID, make_match

CHAMPS = {7: {"name": "LeBlanc", "icon": "x"}, 122: {"name": "Darius", "icon": "y"}, 1: {"name": "Annie", "icon": "z"}}


def test_stats_calcules_en_python():
    game = stats.match_stats(make_match(), PUUID, CHAMPS, {3020: "Chaussures du sorcier"})
    me, opp = game["joueur"], game["adversaire_de_lane"]
    assert game["resultat"] == "DEFAITE" and game["role"] == "Mid"
    assert me["champion"] == "LeBlanc" and me["objets"] == ["Chaussures du sorcier"]
    assert me["kda"] == round(5 / 11, 2)
    assert me["cs_par_min"] == 4.9
    # 5 participations sur 18 kills d'equipe (2 + 4 x 4).
    assert me["participation_kills_pct"] == round(5 / 18 * 100)
    assert opp["champion"] == "Darius" and opp["degats_champions"] == 21000
    assert "11 morts" in game["angles_de_moquerie"]


def test_bonne_game_a_quand_meme_des_angles():
    match = make_match(win=True)
    match["info"]["participants"][0].update(
        kills=15, deaths=0, assists=10, totalMinionsKilled=300, totalDamageDealtToChampions=40000,
        goldEarned=20000, visionScore=60, visionWardsBoughtInGame=3, totalTimeSpentDead=0,
    )
    game = stats.match_stats(match, PUUID, CHAMPS, {})
    assert game["angles_de_moquerie"]


def test_aram_et_remake_ignores():
    assert stats.match_stats(make_match(queue=450), PUUID, CHAMPS, {}) is None
    assert stats.match_stats(make_match(duration=200), PUUID, CHAMPS, {}) is None


def test_rang():
    entries = [{"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "IV",
                "leaguePoints": 12, "wins": 47, "losses": 53}]
    assert stats.ranked_summary(entries)["solo_duo"]["winrate_pct"] == 47
    assert "info" in stats.ranked_summary([])
