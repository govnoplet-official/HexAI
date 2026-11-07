"""
Убирает ссылки из поля "d" (описание) во всех JSON-файлах папки.

Правила:
    [текст](url)  -> текст
    голый URL     -> удаляется

Использование:
    python strip_links.py [папка]

По умолчанию: папка categories рядом со скриптом.
Файлы перезаписываются на месте.
"""

import glob
import json
import os
import re
import sys

MD_LINK = re.compile(r"\[([^\]]*)\]\((?:https?://|www\.)[^)]*\)", re.IGNORECASE)
BARE_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
SPACES = re.compile(r"[ \t]{2,}")


def clean(text):
    text = MD_LINK.sub(r"\1", text)
    text = BARE_URL.sub("", text)
    text = SPACES.sub(" ", text)
    return text.strip()


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "categories")

    changed_files = 0
    changed_entries = 0

    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_changes = 0
        for entry in data.values():
            original = entry.get("d")
            if not isinstance(original, str):
                continue
            cleaned = clean(original)
            if cleaned != original:
                entry["d"] = cleaned
                file_changes += 1

        if file_changes:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            changed_files += 1
            changed_entries += file_changes
            print(f"{os.path.basename(path)}: изменено {file_changes}")

    print(f"Файлов изменено: {changed_files}, записей изменено: {changed_entries}")


if __name__ == "__main__":
    main()
