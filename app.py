"""Interface Streamlit : chat qui roast les dernieres games LoL d'un joueur.

Lancement local (venv active) :
    streamlit run app.py
"""

import hmac

import streamlit as st

from src.agent import answer
from src.config import secret

APP_NAME = "Roast LoL"
RIOT_DISCLAIMER = (
    f"{APP_NAME} isn't endorsed by Riot Games and doesn't reflect the views or opinions of "
    "Riot Games or anyone officially involved in producing or managing Riot Games properties. "
    "Riot Games, and all associated properties are trademarks or registered trademarks of "
    "Riot Games, Inc."
)

st.set_page_config(page_title=APP_NAME, page_icon="🔥")


def check_password() -> bool:
    """Mot de passe partage entre potes, pour proteger les quotas Riot et Mistral."""
    if st.session_state.get("authenticated"):
        return True
    expected = secret("APP_PASSWORD")
    if not expected:
        st.error("APP_PASSWORD manquant dans les secrets : acces bloque.")
        return False

    st.title(f"🔥 {APP_NAME}")
    password = st.text_input("Mot de passe", type="password")
    if password:
        # compare_digest : comparaison en temps constant.
        if hmac.compare_digest(password.encode(), expected.encode()):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Mauvais mot de passe. Meme ca tu le rates.")
    return False


def show_table(rows: list[dict]) -> None:
    if rows:
        with st.expander("📊 Les stats utilisees (tout est vrai, desole)"):
            st.dataframe(rows, hide_index=True, use_container_width=True)


if not check_password():
    st.caption(RIOT_DISCLAIMER)
    st.stop()

st.title(f"🔥 {APP_NAME}")
st.caption("Ecris par exemple : parle moi des 2 dernieres games de Pseudo#TAG")

if "history" not in st.session_state:
    st.session_state.history = []

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        show_table(message.get("table", []))

if prompt := st.chat_input("Pseudo#TAG a roaster..."):
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyse du carnage en cours..."):
            llm_history = [
                {"role": m["role"], "content": m["content"]} for m in st.session_state.history
            ]
            try:
                reply = answer(llm_history)
                text, table = reply.text, reply.table
            except Exception as exc:
                text, table = f"Le bot a crash (comme ta lane) : {type(exc).__name__}.", []
        st.markdown(text)
        show_table(table)

    st.session_state.history.append({"role": "assistant", "content": text, "table": table})

st.caption(RIOT_DISCLAIMER)
