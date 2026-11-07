"""
Преобразует special_handlers.json в формат записей папки categories
с дополнительным полем "u" (usage) для ручного заполнения.

Формат записи:
    "<id>": {
        "n": "<base_name>",
        "c": "<namespace из id>",
        "d": "<описание без ссылок>",
        "i": "<inputs>",
        "o": "<outputs>",
        "u": "<как модель должна использовать паттерн, заполняется вручную>"
    }

Использование:
    python special_handlers_to_categories.py [входной.json] [выходной.json]

По умолчанию: special_handlers.json -> special_handlers_u.json (рядом со скриптом).
Если выходной файл уже существует, значения "u" из него сохраняются.
Исходный файл не изменяется.
"""

import json
import os
import sys

from strip_links import clean

EMPTY = "-"


def load_existing_usage(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        existing = json.load(f)
    return {key: entry.get("u", "") for key, entry in existing.items()}


def convert_entry(key, handler, usage):
    operator = handler.get("operator") or {}
    return {
        "n": handler.get("base_name") or handler.get("raw_name") or "",
        "c": key.split(":", 1)[0],
        "d": clean(operator.get("description") or "") or EMPTY,
        "i": operator.get("inputs") or EMPTY,
        "o": operator.get("outputs") or EMPTY,
        "u": usage.get(key, ""),
    }


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "intermediary", "special_handlers.json")
    target = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base_dir, "intermediary", "special_handlers_u.json")

    usage = load_existing_usage(target)

    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {key: convert_entry(key, handler, usage) for key, handler in data.items()}

    with open(target, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    kept = sum(1 for e in result.values() if e["u"])
    print(f"Записей: {len(result)} -> {target}")
    print(f"Заполненных полей u сохранено: {kept}")


if __name__ == "__main__":
    main()
