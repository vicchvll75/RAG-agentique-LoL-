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

import httpx2
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
MISTRAL_UNREACHABLE_MESSAGE = (
    "Impossible de joindre Mistral pour l'instant (coupure réseau). Réessaie dans quelques secondes."
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


class MistralError(Exception):
    """Erreur Mistral, avec un message affichable dans l'appli."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class MistralBusy(MistralError):
    def __init__(self):
        super().__init__(MISTRAL_BUSY_MESSAGE)


class MistralUnreachable(MistralError):
    def __init__(self):
        super().__init__(MISTRAL_UNREACHABLE_MESSAGE)


def _sdk_error_message(status: int, model: str) -> str:
    if status == 401:
        return "La clé Mistral est refusée. Vérifie MISTRAL_API_KEY dans les secrets de l'appli."
    if status == 403:
        return f"Le modèle {model} n'est pas accessible avec cette clé Mistral. Change MISTRAL_MODEL."
    return f"Mistral a renvoyé une erreur {status}. Réessaie, et si ça continue, recharge la page."


@dataclass
class Reply:
    text: str
    display: dict | None = None


def _client() -> Mistral:
    key = secret("MISTRAL_API_KEY")
    if not key:
        raise MistralError("Aucune clé Mistral configurée. Ajoute MISTRAL_API_KEY dans les secrets.")
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
                    temperature=0.4,
                    max_tokens=700,
                )
        except httpx2.TransportError:
            # Coupure reseau ou timeout : un seul nouvel essai rapide.
            if attempt >= 1:
                raise MistralUnreachable() from None
            time.sleep(2)
        except SDKError as exc:
            if exc.status_code != 429:
                raise MistralError(_sdk_error_message(exc.status_code, model)) from None
            if attempt == len(RETRY_WAITS_S):
                raise MistralBusy() from None
            time.sleep(RETRY_WAITS_S[attempt])


def _tag_was_given(riot_id: str, user_text: str) -> bool:
    """Le modele invente parfois un tag (ex. #TAG ou #EUW) : on exige qu'il soit dans le message."""
    if "#" not in riot_id:
        return False
    tag = riot_id.rsplit("#", 1)[1].strip().lower()
    return f"#{tag}" in user_text.replace(" ", "").lower()


def _run_tool(arguments, user_text: str) -> tuple[dict | None, str | None]:
    # user_text : tous les messages de l'utilisateur, pour accepter un tag donne plus tot.
    """Execute l'outil. Renvoie (resultat, None) ou (None, message d'erreur a afficher)."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments or "{}")
    riot_id = str(arguments.get("riot_id", ""))
    if not _tag_was_given(riot_id, user_text):
        name = riot_id.split("#")[0].strip() or "ce joueur"
        return None, (
            f"Il me manque le tag de {name}. Donne-moi le Riot ID complet au format "
            "Pseudo#TAG (le tag est après le # dans le client), je vais pas deviner."
        )
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
    recent = history[-HISTORY_LIMIT:]
    # La conversation envoyee doit commencer par un message de l'utilisateur.
    while recent and recent[0]["role"] != "user":
        recent = recent[1:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *recent]

    try:
        first = _complete(messages, "auto").choices[0].message
    except MistralError as exc:
        return Reply(exc.user_message)

    if not first.tool_calls:
        return Reply(_clean(first.content or ""))

    # Un seul joueur par roast : on traite le premier appel d'outil.
    call = first.tool_calls[0]
    user_text = " ".join(m["content"] for m in history if m["role"] == "user")
    result, error = _run_tool(call.function.arguments, user_text)
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
        "content": result["pour_le_llm"],
    })

    try:
        roast = _complete(messages, "none").choices[0].message.content or ""
    except MistralError as exc:
        return Reply(exc.user_message, result["affichage"])
    return Reply(_clean(roast), result["affichage"])
