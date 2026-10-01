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


def test_tag_invente_par_le_modele(monkeypatch):
    calls = _fake_llm(monkeypatch, [_response(tool_calls=[_tool_call('{"riot_id": "Pseudo#TAG"}')])])
    reply = agent.answer([{"role": "user", "content": "roast Pseudo stp"}])
    assert "tag" in reply.text and calls == ["auto"]


def test_tag_avec_espace_accepte():
    assert agent._tag_was_given("AdolphSingler#667", "parle moi de AdolphSingler #667")


def test_cle_riot_expiree(monkeypatch):
    _fake_llm(monkeypatch, [_response(tool_calls=[_tool_call('{"riot_id": "A#EUW"}')])])

    def boom(**_):
        raise riot_api.RiotAuthError("x")

    monkeypatch.setattr(agent, "get_player_games", boom)
    assert "expiré" in agent.answer([{"role": "user", "content": "A#EUW"}]).text


def test_mistral_sature(monkeypatch):
    _fake_llm(monkeypatch, [agent.MistralBusy()])
    assert agent.answer([{"role": "user", "content": "A#EUW"}]).text == agent.MISTRAL_BUSY_MESSAGE


def test_mistral_injoignable(monkeypatch):
    _fake_llm(monkeypatch, [agent.MistralUnreachable()])
    assert agent.answer([{"role": "user", "content": "A#EUW"}]).text == agent.MISTRAL_UNREACHABLE_MESSAGE


def test_cle_mistral_refusee(monkeypatch):
    _fake_llm(monkeypatch, [agent.MistralError(agent._sdk_error_message(401, "m"))])
    assert "clé Mistral" in agent.answer([{"role": "user", "content": "A#EUW"}]).text


def test_tag_donne_dans_un_message_precedent(monkeypatch):
    _fake_llm(monkeypatch, [
        _response(tool_calls=[_tool_call('{"riot_id": "A#EUW"}')]),
        _response("roast"),
    ])
    monkeypatch.setattr(agent, "get_player_games",
                        lambda **_: {"pour_le_llm": "x", "affichage": {"games": []}})
    history = [
        {"role": "user", "content": "parle moi de A #EUW"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "et sa derniere game ?"},
    ]
    assert agent.answer(history).text == "roast"


def test_historique_commence_par_l_utilisateur(monkeypatch):
    seen = []

    def complete(messages, tool_choice):
        seen.append(messages)
        return _response("ok")

    monkeypatch.setattr(agent, "_complete", complete)
    history = [{"role": r, "content": "x"} for r in ["user", "assistant"] * 4]
    history.append({"role": "user", "content": "y"})
    agent.answer(history)
    assert seen[0][1]["role"] == "user"


def test_roast_complet(monkeypatch):
    calls = _fake_llm(monkeypatch, [
        _response(tool_calls=[_tool_call({"riot_id": "A#EUW", "count": 2})]),
        _response("Miskine, 11 morts."),
    ])
    monkeypatch.setattr(agent, "get_player_games",
                        lambda **_: {"pour_le_llm": "JOUEUR : A#EUW", "affichage": {"games": []}})
    reply = agent.answer([{"role": "user", "content": "A#EUW"}])
    assert reply.text == "Miskine, 11 morts." and reply.display == {"games": []}
    assert calls == ["auto", "none"]
