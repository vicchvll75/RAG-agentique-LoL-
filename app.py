"""LoL Analyzer : chat qui analyse (et descend) les dernières games d'un joueur.

Lancement local (venv active) :
    streamlit run app.py
"""

import streamlit as st

from src import ui
from src.agent import answer

RIOT_DISCLAIMER = (
    "LoL Analyzer isn't endorsed by Riot Games and doesn't reflect the views or opinions of "
    "Riot Games or anyone officially involved in producing or managing Riot Games properties. "
    "Riot Games, and all associated properties are trademarks or registered trademarks of "
    "Riot Games, Inc."
)

st.set_page_config(page_title="LoL Analyzer", layout="centered")
st.markdown(ui.CSS, unsafe_allow_html=True)


def legal_footer() -> None:
    # Mention exigee par les regles Riot pour les applis utilisant leur API.
    st.markdown(f'<div class="legal">{RIOT_DISCLAIMER}</div>', unsafe_allow_html=True)


def show_details(display: dict | None, expanded: bool) -> None:
    if not display or not display.get("games"):
        return
    games = display["games"]
    st.markdown(ui.player_card(display), unsafe_allow_html=True)
    label = f"Statistiques des {len(games)} games" if len(games) > 1 else "Statistiques de la game"
    with st.expander(label, expanded=expanded):
        st.markdown("".join(ui.game_card(g) for g in games), unsafe_allow_html=True)


st.markdown(ui.hero("Tes dernières games, analysées sans pitié."), unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []

if not st.session_state.history:
    st.markdown(
        '<div class="empty"><div class="title">Comment ça marche</div><ul>'
        "<li>Donne un Riot ID complet : <code>Pseudo#TAG</code></li>"
        "</ul></div>",
        unsafe_allow_html=True,
    )

last = len(st.session_state.history) - 1
for i, message in enumerate(st.session_state.history):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        show_details(message.get("display"), expanded=(i == last))

if prompt := st.chat_input("Ex. : analyse les 2 dernières games de Pseudo#TAG"):
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Récupération des games et analyse en cours..."):
            llm_history = [
                {"role": m["role"], "content": m["content"]} for m in st.session_state.history
            ]
            try:
                reply = answer(llm_history)
                text, display = reply.text, reply.display
            except Exception as exc:
                text, display = f"Erreur inattendue ({type(exc).__name__}). Réessaie.", None
        st.markdown(text)
        show_details(display, expanded=True)

    st.session_state.history.append({"role": "assistant", "content": text, "display": display})

legal_footer()
