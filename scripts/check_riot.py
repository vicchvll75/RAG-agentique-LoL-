"""Verifie la cle Riot et la chaine complete sur un Riot ID, sans appeler Mistral.

Usage (depuis la racine du depot, venv active) :
    python -m scripts.check_riot "Pseudo#TAG" 2
"""

import json
import sys

from src.riot_api import RiotError
from src.tools import ToolError, get_player_games


def main() -> None:
    riot_id = sys.argv[1] if len(sys.argv) > 1 else ""
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    try:
        result = get_player_games(riot_id, count)
    except ToolError as exc:
        print(f"Erreur outil : {exc.user_message}")
        return
    except RiotError as exc:
        print(f"Erreur Riot : {exc.user_message}")
        return
    print(json.dumps(result["pour_le_llm"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
