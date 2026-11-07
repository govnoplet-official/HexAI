"""
Разносит разделы "patterns", "special_handlers" и "pregenerated_numbers"
из registry.json в отдельные JSON-файлы. Остальные разделы не сохраняются.

Использование:
    python split_registry.py <registry.json>

Файлы создаются в той же папке, что и исходный файл:
    patterns.json, special_handlers.json, pregenerated_numbers.json
"""

import json
import os
import sys

SECTIONS = ["patterns", "special_handlers", "pregenerated_numbers"]


def main():
    if len(sys.argv) != 2:
        print("Использование: python split_registry.py <registry.json>", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    out_dir = os.path.dirname(os.path.abspath(source))

    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing = [name for name in SECTIONS if name not in data]
    if missing:
        print(f"В файле не найдены разделы: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    for name in SECTIONS:
        target = os.path.join(out_dir, name + ".json")
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data[name], f, ensure_ascii=False, indent=2)
        print(f"{name}: {len(data[name])} записей -> {target}")


if __name__ == "__main__":
    main()
