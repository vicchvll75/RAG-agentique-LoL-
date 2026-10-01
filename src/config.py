"""Configuration : secrets (st.secrets) et constantes."""

import streamlit as st
import truststore

# Utilise le magasin de certificats Windows (antivirus ou proxy qui inspectent le HTTPS).
# Sans effet genant sur Streamlit Cloud (Linux).
truststore.inject_into_ssl()


def secret(name: str, default: str | None = None) -> str | None:
    """Lit un secret : st.secrets en ligne, .streamlit/secrets.toml en local."""
    try:
        value = st.secrets.get(name)
    except Exception:
        # Pas de fichier de secrets du tout (ex. tests).
        value = None
    return value if value else default


# Riot : plateforme (league v4) et route regionale (account v1, match v5).
REGIONS = {
    "EUW": ("euw1", "europe"),
    "EUNE": ("eun1", "europe"),
    "NA": ("na1", "americas"),
    "KR": ("kr", "asia"),
}
DEFAULT_REGION = "EUW"
DEFAULT_GAMES = 2
MAX_GAMES = 10

# Mistral : modele modifiable dans les secrets sans toucher au code.
# mistral-small-latest renvoie 429 en continu sur l'offre gratuite de ce compte,
# ministral-8b-latest repond et gere le function calling.
DEFAULT_MISTRAL_MODEL = "ministral-8b-latest"

CACHE_DIR = ".cache"
