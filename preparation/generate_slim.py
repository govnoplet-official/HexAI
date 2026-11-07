"""
Генерирует slim-версию базы паттернов для ИИ.

Формат записи:
    "<id>": {
        "n": "<name>",
        "c": "<категория, namespace из id>",
        "d": "<описания операторов через ' | '>",
        "i": "<входы операторов через ' | '>",
        "o": "<выходы операторов через ' | '>"
    }

Использование:
    python generate_slim.py [входной.json] [выходной.json]

По умолчанию: patterns.json -> patterns_slim.json (в папке скрипта).
Исходный файл не изменяется.
"""

import json
import os
import sys

EMPTY = "-"


def slim_entry(entry):
    operators = entry.get("operators") or []
    category = entry["id"].split(":", 1)[0]

    return {
        "n": entry.get("name", ""),
        "c": category,
        "d": " | ".join(op.get("description") or EMPTY for op in operators) or EMPTY,
        "i": " | ".join(op.get("inputs") or EMPTY for op in operators) or EMPTY,
        "o": " | ".join(op.get("outputs") or EMPTY for op in operators) or EMPTY,
    }


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "intermediary", "patterns.json")
    target = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base_dir, "intermediary", "patterns_slim.json")

    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)

    slim = {key: slim_entry(entry) for key, entry in data.items()}

    with open(target, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Записей: {len(slim)} -> {target}")


if __name__ == "__main__":
    main()
