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
# Sur l'offre gratuite de ce compte, small, medium et magistral renvoient 429 en continu.
# open-mistral-nemo (12B) repond et cite les chiffres bien plus fidelement que ministral-8b.
DEFAULT_MISTRAL_MODEL = "open-mistral-nemo"

CACHE_DIR = ".cache"
