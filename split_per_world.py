"""
Выносит паттерны с is_per_world == true из patterns.json в отдельный файл.

Использование:
    python split_per_world.py <patterns.json>

Рядом создаются:
    patterns_per_world.json  - паттерны с is_per_world == true
    <patterns.json>.bak      - резервная копия исходного файла
В исходном файле остаются только паттерны с is_per_world != true.
"""

import json
import os
import shutil
import sys


def main():
    if len(sys.argv) != 2:
        print("Использование: python split_per_world.py <patterns.json>", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    out_dir = os.path.dirname(os.path.abspath(source))
    target = os.path.join(out_dir, "patterns_per_world.json")

    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)

    per_world = {k: v for k, v in data.items() if v.get("is_per_world") is True}
    rest = {k: v for k, v in data.items() if v.get("is_per_world") is not True}

    shutil.copyfile(source, source + ".bak")

    with open(target, "w", encoding="utf-8") as f:
        json.dump(per_world, f, ensure_ascii=False, indent=2)

    with open(source, "w", encoding="utf-8") as f:
        json.dump(rest, f, ensure_ascii=False, indent=2)

    print(f"is_per_world = true: {len(per_world)} -> {target}")
    print(f"Осталось в {source}: {len(rest)}")
    print(f"Резервная копия: {source}.bak")


if __name__ == "__main__":
    main()
