"""Rendu HTML de l'interface : styles, carte du joueur et cartes de games."""

from html import escape

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown, .stChatInput textarea { font-family: 'Inter', sans-serif; }
.stApp { background: radial-gradient(1200px 600px at 50% -10%, #142231 0%, #0A0E13 60%); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 860px; padding-top: 2.5rem; padding-bottom: 7rem; }

.hero { text-align: center; margin: 0 0 1.8rem 0; }
.hero .brand {
  font-family: 'Cinzel', serif; font-weight: 700; font-size: 2.6rem; letter-spacing: .12em;
  background: linear-gradient(180deg, #F0E6D2 0%, #C8AA6E 70%, #785A28 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent; line-height: 1.1;
}
.hero .line { width: 120px; height: 1px; margin: .8rem auto; background: linear-gradient(90deg, transparent, #C8AA6E, transparent); }
.hero .tagline { color: #8B95A3; font-size: .95rem; }

.empty { border: 1px solid #1F2B38; background: #0F161E; border-radius: 14px; padding: 1.2rem 1.4rem; }
.empty .title { color: #F0E6D2; font-weight: 600; margin-bottom: .6rem; }
.empty code { background: #1A2430; color: #C8AA6E; padding: .15rem .45rem; border-radius: 6px; font-size: .85rem; }
.empty ul { margin: 0; padding-left: 1.1rem; color: #8B95A3; }
.empty li { margin: .3rem 0; }

[data-testid="stChatMessage"] { background: transparent; padding: .4rem 0; }
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] { display: none; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
  margin-left: auto; max-width: 75%; background: #1A2430; border: 1px solid #1F2B38;
  border-radius: 14px 14px 4px 14px; padding: .6rem 1rem;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {
  background: #121A23; border: 1px solid #1F2B38; border-left: 3px solid #C8AA6E;
  border-radius: 4px 14px 14px 14px; padding: .9rem 1.2rem;
}
[data-testid="stChatInput"] { border: 1px solid #1F2B38; border-radius: 12px; }
[data-testid="stExpander"] details { border: 1px solid #1F2B38; border-radius: 12px; background: #0F161E; }

.player { display: flex; align-items: center; gap: 1rem; padding: .9rem 1rem; margin: .4rem 0 .9rem 0;
  border: 1px solid #1F2B38; border-radius: 12px; background: linear-gradient(90deg, #15202B, #0F161E); flex-wrap: wrap; }
.player .pfp { width: 56px; height: 56px; border-radius: 50%; border: 2px solid #C8AA6E; }
.player .pname { font-weight: 700; font-size: 1.1rem; color: #F0E6D2; }
.player .pname span { color: #8B95A3; font-weight: 500; }
.player .pmeta { color: #8B95A3; font-size: .8rem; margin-top: .15rem; }
.player .ranks { display: flex; gap: .6rem; margin-left: auto; flex-wrap: wrap; }
.rank { border: 1px solid #1F2B38; border-radius: 10px; padding: .45rem .75rem; background: #121A23; min-width: 130px; }
.rank .rq { font-size: .68rem; text-transform: uppercase; letter-spacing: .08em; color: #8B95A3; }
.rank .rv { font-weight: 700; color: #C8AA6E; font-size: .92rem; }
.rank .rw { font-size: .75rem; color: #8B95A3; }

.game { display: flex; gap: 1rem; padding: .9rem 1rem; margin: .6rem 0; border-radius: 12px;
  background: #121A23; border: 1px solid #1F2B38; border-left: 4px solid #E84057; }
.game.win { border-left-color: #3FB68B; }
.g-left { width: 92px; flex-shrink: 0; text-align: center; }
.g-left img { width: 64px; height: 64px; border-radius: 10px; border: 1px solid #1F2B38; }
.g-res { font-weight: 700; font-size: .78rem; letter-spacing: .08em; margin-top: .35rem; color: #E84057; }
.game.win .g-res { color: #3FB68B; }
.g-sub { font-size: .7rem; color: #8B95A3; line-height: 1.35; margin-top: .15rem; }
.g-main { flex: 1; min-width: 0; }
.g-head { display: flex; align-items: baseline; gap: .6rem; flex-wrap: wrap; }
.g-champ { font-weight: 700; color: #F0E6D2; font-size: 1.05rem; }
.g-role { font-size: .72rem; color: #8B95A3; border: 1px solid #1F2B38; border-radius: 999px; padding: .05rem .5rem; }
.g-kda { margin-left: auto; font-weight: 700; font-size: 1.05rem; color: #F0E6D2; }
.g-kda .d { color: #E84057; }
.g-kda small { color: #8B95A3; font-weight: 500; font-size: .75rem; margin-left: .35rem; }
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .5rem; margin-top: .6rem; }
.metric { background: #0F161E; border: 1px solid #1F2B38; border-radius: 8px; padding: .4rem .5rem; }
.metric .ml { font-size: .64rem; text-transform: uppercase; letter-spacing: .07em; color: #8B95A3; }
.metric .mv { font-weight: 700; font-size: .95rem; color: #E6E1D6; }
.metric .ms { font-size: .68rem; color: #8B95A3; }
.vs { display: flex; align-items: center; gap: .5rem; margin-top: .6rem; font-size: .78rem; color: #8B95A3; flex-wrap: wrap; }
.vs img { width: 22px; height: 22px; border-radius: 6px; }
.vs b { color: #C9D1DB; font-weight: 600; }
.chip { border-radius: 999px; padding: .05rem .5rem; font-weight: 600; font-size: .72rem; }
.chip.pos { color: #3FB68B; background: rgba(63,182,139,.12); }
.chip.neg { color: #E84057; background: rgba(232,64,87,.12); }

.legal { margin-top: 2.5rem; text-align: center; font-size: .62rem; color: #3E4752; line-height: 1.4; }

@media (max-width: 640px) {
  .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .g-left { width: 70px; } .g-left img { width: 52px; height: 52px; }
  .hero .brand { font-size: 2rem; }
}
</style>
"""


def _n(value: int) -> str:
    """12345 vers 12 345 (espace fine insecable)."""
    return f"{value:,}".replace(",", " ")


def _chip(diff: float, unit: str = "", decimals: int = 0) -> str:
    sign = "+" if diff > 0 else ""
    text = f"{diff:.{decimals}f}" if decimals else _n(int(diff))
    css = "pos" if diff >= 0 else "neg"
    return f'<span class="chip {css}">{sign}{text}{unit}</span>'


def _metric(label: str, value: str, sub: str = "") -> str:
    return f'<div class="metric"><div class="ml">{label}</div><div class="mv">{value}</div><div class="ms">{sub}</div></div>'


def _rank(raw: str) -> str:
    """GOLD IV 12 LP vers Gold IV · 12 LP."""
    parts = raw.split()
    if len(parts) >= 4:
        return f"{parts[0].capitalize()} {parts[1]} · {parts[2]} LP"
    return raw.capitalize()


def hero(tagline: str) -> str:
    return (
        '<div class="hero"><div class="brand">LOL ANALYZER</div><div class="line"></div>'
        f'<div class="tagline">{escape(tagline)}</div></div>'
    )


def player_card(display: dict) -> str:
    name, _, tag = display["joueur"].partition("#")
    icon = f'<img class="pfp" src="{escape(display["icone"])}">' if display.get("icone") else ""
    meta = " · ".join(
        x for x in (f"Niveau {display['niveau']}" if display.get("niveau") else "", display["region"]) if x
    )
    ranks = ""
    labels = {"solo_duo": "Solo / Duo", "flex": "Flex"}
    for key, label in labels.items():
        entry = display["classement"].get(key)
        if entry:
            ranks += (
                f'<div class="rank"><div class="rq">{label}</div><div class="rv">{escape(_rank(entry["rang"]))}</div>'
                f'<div class="rw">{entry["winrate_pct"]} % WR · {entry["victoires"]}V {entry["defaites"]}D</div></div>'
            )
    if not ranks:
        ranks = '<div class="rank"><div class="rq">Classé</div><div class="rv">Non classé</div></div>'
    return (
        f'<div class="player">{icon}<div><div class="pname">{escape(name)}<span>#{escape(tag)}</span></div>'
        f'<div class="pmeta">{escape(meta)}</div></div><div class="ranks">{ranks}</div></div>'
    )


def game_card(game: dict) -> str:
    me, opp = game["joueur"], game["adversaire_de_lane"]
    win = game["resultat"] == "VICTOIRE"
    dead_min, dead_s = divmod(me["temps_mort_s"], 60)
    icon = f'<img src="{escape(me["icone"])}">' if me.get("icone") else ""

    metrics = "".join([
        _metric("CS/min", f"{me['cs_par_min']}", f"{me['cs']} CS"),
        _metric("Dégâts", _n(me["degats_champions"]), f"{me['part_degats_equipe_pct']} % équipe"),
        _metric("Kill part.", f"{me['participation_kills_pct']} %", ""),
        _metric("Vision", f"{me['score_vision']}", f"{me['pinks_achetees']} pink" + ("s" if me["pinks_achetees"] > 1 else "")),
        _metric("Temps mort", f"{dead_min}:{dead_s:02d}", ""),
    ])

    vs = ""
    if opp:
        opp_icon = f'<img src="{escape(opp["icone"])}">' if opp.get("icone") else ""
        vs = (
            f'<div class="vs">{opp_icon}Face à <b>{escape(opp["champion"])}</b>'
            f'<span>{opp["kills"]}/{opp["morts"]}/{opp["assists"]}</span>'
            f'<span>CS/min {_chip(me["cs_par_min"] - opp["cs_par_min"], decimals=1)}</span>'
            f'<span>Dégâts {_chip(me["degats_champions"] - opp["degats_champions"])}</span>'
            f'<span>Or {_chip(me["or"] - opp["or"])}</span></div>'
        )

    queue = escape(game["file"])
    return (
        f'<div class="game {"win" if win else "loss"}">'
        f'<div class="g-left">{icon}<div class="g-res">{"VICTOIRE" if win else "DÉFAITE"}</div>'
        f'<div class="g-sub">{queue}<br>{escape(game["duree"])}</div></div>'
        f'<div class="g-main"><div class="g-head"><span class="g-champ">{escape(me["champion"])}</span>'
        f'<span class="g-role">{escape(game["role"])}</span>'
        f'<span class="g-kda">{me["kills"]} / <span class="d">{me["morts"]}</span> / {me["assists"]}'
        f'<small>{me["kda"]} KDA</small></span></div>'
        f'<div class="metrics">{metrics}</div>{vs}</div></div>'
    )
