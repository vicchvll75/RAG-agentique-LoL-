from types import SimpleNamespace

from src import agent, riot_api


def _response(content="", tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _tool_call(arguments):
    return SimpleNamespace(id="c1", function=SimpleNamespace(name="get_player_games", arguments=arguments))


def _fake_llm(monkeypatch, responses):
    """Remplace Mistral par des reponses prevues ; renvoie la liste des tool_choice utilises."""
    calls = []

    def complete(messages, tool_choice):
        calls.append(tool_choice)
        item = responses[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(agent, "_complete", complete)
    return calls


def test_demande_sans_rapport(monkeypatch):
    calls = _fake_llm(monkeypatch, [_response("Je roast que des joueurs LoL, donne un Pseudo#TAG.")])
    reply = agent.answer([{"role": "user", "content": "recette des crepes"}])
    assert "Pseudo#TAG" in reply.text and calls == ["auto"]


def test_tag_manquant_sans_second_appel(monkeypatch):
    calls = _fake_llm(monkeypatch, [_response(tool_calls=[_tool_call('{"riot_id": "Pseudo"}')])])
    reply = agent.answer([{"role": "user", "content": "roast Pseudo"}])
    assert "Pseudo#TAG" in reply.text and calls == ["auto"]


def test_cle_riot_expiree(monkeypatch):
    _fake_llm(monkeypatch, [_response(tool_calls=[_tool_call('{"riot_id": "A#EUW"}')])])

    def boom(**_):
        raise riot_api.RiotAuthError("x")

    monkeypatch.setattr(agent, "get_player_games", boom)
    assert "expire" in agent.answer([{"role": "user", "content": "A#EUW"}]).text


def test_mistral_sature(monkeypatch):
    _fake_llm(monkeypatch, [agent.MistralBusy()])
    assert agent.answer([{"role": "user", "content": "A#EUW"}]).text == agent.MISTRAL_BUSY_MESSAGE


def test_roast_complet(monkeypatch):
    calls = _fake_llm(monkeypatch, [
        _response(tool_calls=[_tool_call({"riot_id": "A#EUW", "count": 2})]),
        _response("Miskine, 11 morts."),
    ])
    monkeypatch.setattr(agent, "get_player_games",
                        lambda **_: {"pour_le_llm": {"x": 1}, "tableau": [{"KDA": 0.45}]})
    reply = agent.answer([{"role": "user", "content": "A#EUW"}])
    assert reply.text == "Miskine, 11 morts." and reply.table == [{"KDA": 0.45}]
    assert calls == ["auto", "none"]
