"""
Готовит данные паттернов для модели:
  1. Берёт категории из папки categories и special_handlers_u.json.
  2. Оставляет только паттерны из установленных модов (mods_config.json).
  3. Из special_handlers_u.json убирает записи с пустым полем "u".
  4. Убирает префикс мода из id, если короткое имя уникально среди всех
     включённых паттернов. При коллизии полный id сохраняется.
  5. Добавляет описание категории (_description) из categories/_descriptions.json
     первым полем в каждый файл, если описание есть.

Использование:
    python prepare_categories.py [конфиг.json]
"""

import collections
import glob
import json
import os
import sys

SPECIAL_FILE = "special_handlers_u.json"
DESCRIPTIONS_FILE = "category_descriptions.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "mods_config.json")

    config = load_json(config_path)
    input_dir = os.path.join(base_dir, config["input_dir"])
    output_dir = os.path.join(base_dir, config["output_dir"])
    mods = config["mods"]
    enabled = {name for name, on in mods.items() if on is True}

    if not enabled:
        print("Ни один мод не включён в конфиге, выход.")
        sys.exit(1)

    sources = {}
    descriptions = {}
    for path in sorted(glob.glob(os.path.join(input_dir, "*.json"))):
        raw = load_json(path)
        name = os.path.basename(path)
        if "_description" in raw:
            descriptions[name] = raw["_description"]
        sources[name] = {k: v for k, v in raw.items() if not k.startswith("_")}

    special_raw = load_json(os.path.join(base_dir, "intermediary", SPECIAL_FILE))
    special_filled = {
        key: entry for key, entry in special_raw.items()
        if isinstance(entry.get("u"), str) and entry["u"].strip()
    }
    special_dropped = len(special_raw) - len(special_filled)
    sources[SPECIAL_FILE] = special_filled

    short_owners = collections.defaultdict(set)
    for data in sources.values():
        for key in data:
            namespace, short = key.split(":", 1)
            if namespace in enabled:
                short_owners[short].add(key)

    os.makedirs(output_dir, exist_ok=True)
    for old in glob.glob(os.path.join(output_dir, "*.json")):
        os.remove(old)

    unknown = set()
    total_kept = 0
    total_source = 0
    total_shortened = 0

    for name, data in sources.items():
        result = {}
        for key, entry in data.items():
            total_source += 1
            namespace, short = key.split(":", 1)
            if namespace not in mods:
                unknown.add(namespace)
            if namespace not in enabled:
                continue
            if len(short_owners[short]) == 1:
                result[short] = entry
                total_shortened += 1
            else:
                result[key] = entry

        # special_handlers_u.json пишется всегда, даже если все записи отфильтрованы.
        if result or name == SPECIAL_FILE:
            kept_count = len(result)
            total_kept += kept_count
            if name in descriptions and result:
                result = {"_description": descriptions[name], **result}
            out_path = os.path.join(output_dir, name)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"{name}: {kept_count} из {len(data)}")

    collisions = sorted(s for s, owners in short_owners.items() if len(owners) > 1)

    print(f"Special handlers без поля u (отброшены): {special_dropped}")
    print(f"Итого оставлено: {total_kept} из {total_source} -> {output_dir}")
    print(f"Префикс убран у: {total_shortened}, полный id сохранён у: {total_kept - total_shortened}")
    print(f"Коллизии (полный id): {', '.join(collisions) if collisions else 'нет'}")
    print(f"Включённые моды: {', '.join(sorted(enabled))}")
    if unknown:
        print(f"Неизвестные пространства имён (не в конфиге, отфильтрованы): {', '.join(sorted(unknown))}")


if __name__ == "__main__":
    main()
