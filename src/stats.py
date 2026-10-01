"""Calcul des stats d'un match en Python. Le LLM ne fait aucun calcul, il ne fait que rediger."""

from datetime import datetime, timezone

# Files de la Faille de l'invocateur (les seules ou l'adversaire de lane a un sens).
SR_QUEUES = {
    400: "Normale draft",
    420: "Classée solo/duo",
    430: "Normale blind",
    440: "Classée flex",
    480: "Swiftplay",
    490: "Partie rapide",
}
ROLES = {
    "TOP": "Top",
    "JUNGLE": "Jungle",
    "MIDDLE": "Mid",
    "BOTTOM": "ADC",
    "UTILITY": "Support",
}
REMAKE_MAX_S = 300


def _cs(p: dict) -> int:
    return p["totalMinionsKilled"] + p["neutralMinionsKilled"]


def _per_min(value: float, minutes: float) -> float:
    return round(value / minutes, 1) if minutes else 0.0


def _kda(p: dict) -> float:
    return round((p["kills"] + p["assists"]) / max(1, p["deaths"]), 2)


def _line(p: dict, minutes: float, champions: dict[int, dict]) -> dict:
    """Stats brutes d'un participant, utilisees pour le joueur et pour son adversaire."""
    champion = champions.get(p["championId"], {})
    return {
        "champion": champion.get("name", p["championName"]),
        "icone": champion.get("icon"),
        "kills": p["kills"],
        "morts": p["deaths"],
        "assists": p["assists"],
        "kda": _kda(p),
        "cs": _cs(p),
        "cs_par_min": _per_min(_cs(p), minutes),
        "degats_champions": p["totalDamageDealtToChampions"],
        "or": p["goldEarned"],
        "score_vision": p["visionScore"],
        "niveau": p["champLevel"],
    }


def _angles(me: dict, opp: dict | None, role: str) -> list[str]:
    """Faits chiffres moqueables, choisis en Python pour que le LLM ne cherche pas lui meme."""
    angles = []
    if me["morts"] >= 7:
        angles.append(f"{me['morts']} morts")
    if me["temps_mort_s"] >= 150:
        angles.append(f"{me['temps_mort_s'] // 60} min {me['temps_mort_s'] % 60} s passees mort")
    if me["kda"] < 2:
        angles.append(f"KDA de {me['kda']}")
    if role not in ("Support", "Jungle") and me["cs_par_min"] < 6.5:
        angles.append(f"{me['cs_par_min']} CS/min")
    if me["participation_kills_pct"] < 45:
        angles.append(f"participation aux kills de {me['participation_kills_pct']} %")
    if role in ("Top", "Mid", "ADC") and me["part_degats_equipe_pct"] < 20:
        angles.append(f"seulement {me['part_degats_equipe_pct']} % des degats de l'equipe")
    vision_min = me["vision_par_min"]
    if vision_min < (1.5 if role == "Support" else 0.8):
        angles.append(f"vision de {vision_min} par minute")
    if me["pinks_achetees"] == 0:
        angles.append("zero pink achetee")

    if opp:
        if me["cs_par_min"] < opp["cs_par_min"] - 0.5 and role != "Support":
            angles.append(
                f"{me['cs_par_min']} CS/min contre {opp['cs_par_min']} pour {opp['champion']} en face"
            )
        if me["degats_champions"] < opp["degats_champions"]:
            angles.append(
                f"{me['degats_champions']} degats contre {opp['degats_champions']} pour {opp['champion']}"
            )
        if me["or"] < opp["or"] - 1000:
            angles.append(f"{opp['or'] - me['or']} d'or de retard sur {opp['champion']}")

    if not angles:
        # Bonne game : on trouve quand meme un angle, toujours chiffre.
        angles.append(f"score de vision de {me['score_vision']}")
        angles.append(f"{me['morts']} morts quand meme")
    return angles


def match_stats(match: dict, puuid: str, champions: dict[int, dict], items: dict[int, str]) -> dict | None:
    """Resume chiffre d'un match pour un joueur. None si hors Faille ou remake."""
    info = match["info"]
    if info["queueId"] not in SR_QUEUES or info["gameDuration"] < REMAKE_MAX_S:
        return None

    minutes = info["gameDuration"] / 60
    players = info["participants"]
    me_raw = next(p for p in players if p["puuid"] == puuid)
    team = [p for p in players if p["teamId"] == me_raw["teamId"]]
    team_kills = sum(p["kills"] for p in team)
    team_damage = sum(p["totalDamageDealtToChampions"] for p in team)

    position = me_raw.get("teamPosition") or ""
    role = ROLES.get(position, "Inconnu")
    opp_raw = next(
        (p for p in players if p["teamId"] != me_raw["teamId"] and position and p.get("teamPosition") == position),
        None,
    )

    me = _line(me_raw, minutes, champions)
    me.update({
        "participation_kills_pct": round(
            (me_raw["kills"] + me_raw["assists"]) / max(1, team_kills) * 100
        ),
        "part_degats_equipe_pct": round(
            me_raw["totalDamageDealtToChampions"] / max(1, team_damage) * 100
        ),
        "vision_par_min": _per_min(me_raw["visionScore"], minutes),
        "wards_posees": me_raw["wardsPlaced"],
        "pinks_achetees": me_raw["visionWardsBoughtInGame"],
        "temps_mort_s": me_raw["totalTimeSpentDead"],
        "plus_gros_multikill": me_raw["largestMultiKill"],
        "objets": [
            items.get(me_raw[f"item{i}"], str(me_raw[f"item{i}"]))
            for i in range(7)
            if me_raw[f"item{i}"]
        ],
    })
    opp = _line(opp_raw, minutes, champions) if opp_raw else None

    ended = datetime.fromtimestamp(info["gameEndTimestamp"] / 1000, timezone.utc)
    return {
        "match_id": match["metadata"]["matchId"],
        "date_utc": ended.strftime("%Y-%m-%d %H:%M"),
        "file": SR_QUEUES[info["queueId"]],
        "resultat": "VICTOIRE" if me_raw["win"] else "DEFAITE",
        "duree": f"{int(minutes)} min {info['gameDuration'] % 60:02d} s",
        "role": role,
        "joueur": me,
        "adversaire_de_lane": opp,
        "angles_de_moquerie": _angles(me, opp, role),
    }


def ranked_summary(entries: list[dict]) -> dict:
    """Rang et winrate global par file classee."""
    labels = {"RANKED_SOLO_5x5": "solo_duo", "RANKED_FLEX_SR": "flex"}
    summary = {}
    for entry in entries:
        label = labels.get(entry["queueType"])
        if not label:
            continue
        games = entry["wins"] + entry["losses"]
        summary[label] = {
            "rang": f"{entry['tier']} {entry['rank']} {entry['leaguePoints']} LP",
            "victoires": entry["wins"],
            "defaites": entry["losses"],
            "winrate_pct": round(entry["wins"] / games * 100) if games else 0,
        }
    return summary or {"info": "aucune partie classee cette saison"}



def for_llm(value):
    """Copie du resume sans les URLs d'icones (inutiles au LLM, et autant de tokens en moins)."""
    if isinstance(value, dict):
        return {k: for_llm(v) for k, v in value.items() if k != "icone"}
    if isinstance(value, list):
        return [for_llm(v) for v in value]
    return value
