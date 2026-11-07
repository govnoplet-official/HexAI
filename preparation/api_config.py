"""
Загрузка настроек API из config.json (в корне проекта).

config.json не хранится в git (см. .gitignore).
Шаблон с плейсхолдерами: config.example.json.

Использование:
    from api_config import load_api_config
    cfg = load_api_config()
    cfg["base_url"], cfg["api_keys"]
"""

import json
import os
import sys

CONFIG_NAME = "config.json"
PLACEHOLDER_MARKER = "YOUR_"


def load_api_config(path=None):
    if path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, CONFIG_NAME)

    if not os.path.exists(path):
        sys.exit(f"Нет файла {path}. Скопируйте config.example.json в {CONFIG_NAME} и заполните.")

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    base_url = cfg.get("base_url", "")
    api_keys = [k for k in cfg.get("api_keys", []) if isinstance(k, str) and k.strip()]

    if not base_url or PLACEHOLDER_MARKER in base_url or "example.com" in base_url:
        sys.exit(f"В {path} не задан реальный base_url.")
    if not api_keys or any(k.startswith(PLACEHOLDER_MARKER) for k in api_keys):
        sys.exit(f"В {path} не заданы реальные api_keys (остались плейсхолдеры).")

    return {"base_url": base_url.rstrip("/"), "api_keys": api_keys}
