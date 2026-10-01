"""Cache disque en JSON (matchs termines, fichiers Data Dragon)."""

import json
import time
from pathlib import Path

from src.config import CACHE_DIR


def _path(key: str) -> Path:
    return Path(CACHE_DIR) / f"{key}.json"


def read(key: str, max_age_s: float | None = None):
    """Renvoie la valeur en cache, ou None si absente ou trop vieille."""
    path = _path(key)
    if not path.exists():
        return None
    if max_age_s is not None and time.time() - path.stat().st_mtime > max_age_s:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(key: str, value) -> None:
    path = _path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
