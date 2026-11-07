"""
Разбивает p_c_s.json на отдельный JSON для каждой категории (поле "c").

Использование:
    python split_by_category.py [входной.json] [папка_вывода]

По умолчанию: p_c_s.json -> папка categories рядом со скриптом.
Имя файла категории берётся из значения поля "c".
Исходный файл не изменяется.
"""

import json
import os
import re
import sys
from collections import defaultdict


def safe_name(category):
    # Убираем символы, недопустимые в именах файлов Windows.
    return re.sub(r'[<>:"/\\|?*]', "_", str(category)).strip() or "uncategorized"


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "intermediary", "p_c_s.json")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base_dir, "categories")

    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)

    groups = defaultdict(dict)
    for key, entry in data.items():
        category = entry.get("c") or "uncategorized"
        groups[category][key] = entry

    os.makedirs(out_dir, exist_ok=True)

    for category, entries in sorted(groups.items()):
        path = os.path.join(out_dir, f"{safe_name(category)}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f"{category}: {len(entries)} -> {path}")

    total = sum(len(v) for v in groups.values())
    print(f"Всего категорий: {len(groups)}, записей: {total} (исходно: {len(data)})")


if __name__ == "__main__":
    main()
