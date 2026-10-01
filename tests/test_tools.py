import pytest

from src import riot_api, tools
from tests.conftest import make_match


def test_tag_manquant():
    with pytest.raises(tools.ToolError):
        tools.parse_riot_id("Pseudo")
    assert tools.parse_riot_id(" Pseudo #EUW ") == ("Pseudo", "EUW")
    assert tools.parse_riot_id("Le Pseudo#1234") == ("Le Pseudo", "1234")


def _fake_riot(monkeypatch, *, account=None, ids=(), matches=None):
    def get_account(*_):
        if account is None:
            raise riot_api.RiotNotFound("x")
        return account

    monkeypatch.setattr(riot_api, "get_account", get_account)
    monkeypatch.setattr(riot_api, "get_match_ids", lambda *_: list(ids))
    monkeypatch.setattr(riot_api, "get_match", lambda match_id, _: matches[match_id])
    monkeypatch.setattr(riot_api, "get_ranked_entries", lambda *_: [])
    monkeypatch.setattr(riot_api, "get_summoner", lambda *_: {"summonerLevel": 30, "profileIconId": 1})
    monkeypatch.setattr("src.ddragon.profile_icon_url", lambda icon_id: f"icon{icon_id}")


def test_riot_id_inexistant(monkeypatch, no_ddragon):
    _fake_riot(monkeypatch)
    with pytest.raises(tools.ToolError, match="existe pas"):
        tools.get_player_games("Fantome#EUW")


def test_joueur_sans_games(monkeypatch, no_ddragon):
    _fake_riot(monkeypatch, account={"puuid": "p"}, ids=["A"], matches={"A": make_match(queue=450)})
    with pytest.raises(tools.ToolError, match="aucune game"):
        tools.get_player_games("Aramien#EUW")


def test_count_borne_et_filtre_faille(monkeypatch, no_ddragon):
    matches = {"A": make_match("A", queue=450), "B": make_match("B"), "C": make_match("C")}
    _fake_riot(monkeypatch, account={"puuid": "puuid-moi", "gameName": "Moi", "tagLine": "EUW"},
               ids=["A", "B", "C"], matches=matches)
    result = tools.get_player_games("Moi#EUW", count=99)
    assert [g["match_id"] for g in result["affichage"]["games"]] == ["B", "C"]
    assert "=== GAME 2" in result["pour_le_llm"] and "GAME 3" not in result["pour_le_llm"]
    assert len(result["affichage"]["games"]) == 2
    assert result["affichage"]["niveau"] == 30
    assert "icone" not in str(result["pour_le_llm"])


class FakeResponse:
    def __init__(self, status, headers=None):
        self.status_code, self.headers = status, headers or {}

    def json(self):
        return {"ok": True}


def test_cle_expiree(monkeypatch):
    monkeypatch.setattr(riot_api.SESSION, "get", lambda *a, **k: FakeResponse(403))
    with pytest.raises(riot_api.RiotAuthError):
        riot_api._get("https://x")


def test_cle_manquante(monkeypatch):
    monkeypatch.setattr("src.riot_api.secret", lambda name, default=None: None)
    with pytest.raises(riot_api.RiotMissingKey):
        riot_api._get("https://x")


def test_rate_limit_riot_attend_puis_reussit(monkeypatch):
    responses = iter([FakeResponse(429, {"Retry-After": "1"}), FakeResponse(200)])
    sleeps = []
    monkeypatch.setattr(riot_api.SESSION, "get", lambda *a, **k: next(responses))
    monkeypatch.setattr(riot_api.time, "sleep", sleeps.append)
    assert riot_api._get("https://x") == {"ok": True}
    assert sleeps == [1]


def test_rate_limit_riot_trop_long(monkeypatch):
    monkeypatch.setattr(riot_api.SESSION, "get", lambda *a, **k: FakeResponse(429, {"Retry-After": "120"}))
    with pytest.raises(riot_api.RiotRateLimited):
        riot_api._get("https://x")
