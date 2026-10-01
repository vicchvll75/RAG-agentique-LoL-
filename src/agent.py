"""Agent Mistral : 2 appels LLM maximum par roast.

Appel 1 : le modele comprend la demande et appelle l'outil (ou repond directement si hors sujet).
Appel 2 : le modele ecrit le roast a partir du resume chiffre.
Les erreurs (Riot ID invalide, joueur introuvable, cle expiree) renvoient un message fixe,
sans second appel, pour economiser le quota gratuit.
"""

import json
import threading
import time
from dataclasses import dataclass

from mistralai.client import Mistral
from mistralai.client.errors import SDKError

from src import riot_api
from src.config import DEFAULT_MISTRAL_MODEL, secret
from src.prompts import SYSTEM_PROMPT
from src.tools import TOOLS_SCHEMA, ToolError, get_player_games

# Attentes avant chaque nouvel essai quand Mistral renvoie 429.
RETRY_WAITS_S = (10, 25)
# Nombre de messages d'historique renvoyes au modele (economise des tokens).
HISTORY_LIMIT = 6
# Le quota Mistral est partage par tous les utilisateurs : un seul appel a la fois.
_MISTRAL_LOCK = threading.Lock()

MISTRAL_BUSY_MESSAGE = (
    "Le cerveau du bot est en PLS, trop de monde veut se faire analyser en même temps "
    "(offre gratuite de Mistral, merci la pauvreté). Réessaie dans une minute."
)
RIOT_MESSAGES = {
    riot_api.RiotAuthError: (
        "La clé Riot a expiré (elle dure 24 h, merci Riot). Dis à l'admin de la renouveler, "
        "en attendant t'es sauvé."
    ),
    riot_api.RiotMissingKey: (
        "Aucune clé Riot n'est configurée, je peux rien analyser. Dis à l'admin d'ajouter "
        "RIOT_API_KEY dans les secrets, en attendant t'es sauvé."
    ),
    riot_api.RiotRateLimited: (
        "Riot me dit de me calmer, trop de requêtes. Réessaie dans une ou deux minutes."
    ),
}


def _clean(text: str) -> str:
    """Le modele met parfois des tirets longs malgre la consigne : on les remplace."""
    for dash in (" \u2014 ", "\u2014", " \u2013 ", "\u2013"):
        text = text.replace(dash, ", ")
    return text.strip()


class MistralBusy(Exception):
    pass


@dataclass
class Reply:
    text: str
    display: dict | None = None


def _client() -> Mistral:
    key = secret("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY manquante dans les secrets.")
    return Mistral(api_key=key)


def _complete(messages: list[dict], tool_choice: str):
    model = secret("MISTRAL_MODEL", DEFAULT_MISTRAL_MODEL)
    client = _client()
    for attempt in range(len(RETRY_WAITS_S) + 1):
        try:
            with _MISTRAL_LOCK:
                return client.chat.complete(
                    model=model,
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice=tool_choice,
                    temperature=0.8,
                    max_tokens=700,
                )
        except SDKError as exc:
            if exc.status_code != 429:
                raise
            if attempt == len(RETRY_WAITS_S):
                raise MistralBusy() from None
            time.sleep(RETRY_WAITS_S[attempt])


def _run_tool(arguments) -> tuple[dict | None, str | None]:
    """Execute l'outil. Renvoie (resultat, None) ou (None, message d'erreur a afficher)."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments or "{}")
    try:
        return get_player_games(**arguments), None
    except ToolError as exc:
        return None, exc.user_message
    except riot_api.RiotError as exc:
        return None, RIOT_MESSAGES.get(type(exc), f"Problème côté Riot : {exc.user_message}")
    except TypeError:
        return None, "J'ai rien compris. Donne-moi un Riot ID au format Pseudo#TAG."


def answer(history: list[dict]) -> Reply:
    """Repond au dernier message de l'historique (liste de {"role", "content"})."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history[-HISTORY_LIMIT:]]

    try:
        first = _complete(messages, "auto").choices[0].message
    except MistralBusy:
        return Reply(MISTRAL_BUSY_MESSAGE)

    if not first.tool_calls:
        return Reply(_clean(first.content or ""))

    # Un seul joueur par roast : on traite le premier appel d'outil.
    call = first.tool_calls[0]
    result, error = _run_tool(call.function.arguments)
    if error:
        return Reply(error)

    messages.append({
        "role": "assistant",
        "content": first.content or "",
        "tool_calls": [{
            "id": call.id,
            "type": "function",
            "function": {"name": call.function.name, "arguments": call.function.arguments},
        }],
    })
    messages.append({
        "role": "tool",
        "name": call.function.name,
        "tool_call_id": call.id,
        "content": json.dumps(result["pour_le_llm"], ensure_ascii=False),
    })

    try:
        roast = _complete(messages, "none").choices[0].message.content or ""
    except MistralBusy:
        return Reply(MISTRAL_BUSY_MESSAGE, result["affichage"])
    return Reply(_clean(roast), result["affichage"])
