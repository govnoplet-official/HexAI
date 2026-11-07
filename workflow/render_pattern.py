"""
Рисует цепочку паттернов Hex Casting в одно PNG-изображение.

Вход - строки цепочки, по одной на строку (формат выводит build_pattern_chain.py):
- сокращённый id из категорий (как выводит stage 2), например runtime_escape;
  полный id из intermediary/patterns.json тоже принимается;
- number(N) - число, раскладывается через n_to_p;
- vector(x, y, z) - вектор, раскладывается через vector_to_pattern;
- готовая строка "НАПРАВЛЕНИЕ сигнатура", например "SOUTH_WEST aeaqaaq".

Id с аргументами (special handlers вида id(аргументы)) не поддерживаются:
у них нет сигнатуры без аргументов, такая строка выводит ошибку.

Использование:
    python render_pattern.py "SOUTH_WEST aeaqaaq" "EAST weaqaa" -o chain.png
    python render_pattern.py -i chain.txt -o chain.png
    python build_pattern_chain.py "запрос" --categories math.json | python render_pattern.py -i - -o chain.png

Если -o не указан, PNG сохраняется в renders/chain.png в корне проекта.

Запускать нужно интерпретатором из venv, где установлены hexnumgen и hex-renderer-py.
"""

import argparse
import json
import os
import re
import sys

WORKFLOW_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(WORKFLOW_DIR)
PATTERNS_PATH = os.path.join(BASE_DIR, "intermediary", "patterns.json")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "renders", "chain.png")

sys.path.insert(0, WORKFLOW_DIR)
from n_to_p import n_to_p  # noqa: E402
from vector_to_pattern import vector_pattern  # noqa: E402

from hex_renderer_py import (  # noqa: E402
    Color,
    CollisionOption,
    GridOptions,
    GridPatternOptions,
    HexGrid,
    Intersections,
    Lines,
    Marker,
    PatternVariant,
    Point,
    Triangle,
)

DIRECTIONS = {
    "EAST",
    "NORTH_EAST",
    "NORTH_WEST",
    "WEST",
    "SOUTH_WEST",
    "SOUTH_EAST",
}
NUMBER_RE = re.compile(r"^number\((-?\d+)\)$")
VECTOR_RE = re.compile(r"^vector\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)$")
PATTERN_LINE_RE = re.compile(r"^([A-Z_]+)\s+([wasdqe]+)$")

IMAGE_SIZE = (1024, 1024)
LINE_THICKNESS = 0.08
MARKER_RADIUS = 0.08
LINE_COLORS = [Color(168, 30, 227, 255), Color(40, 200, 255, 255)]
MARKER_COLOR = Color(255, 255, 255, 255)
ARROW_COLOR = Color(0, 0, 0, 255)
ARROW_RADIUS = 0.2
ARROW_BORDER_RADIUS = 0.1


def load_patterns():
    """Возвращает словарь полный id -> запись паттерна из intermediary/patterns.json."""
    with open(PATTERNS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def resolve_pattern_id(short_id, patterns):
    """Находит полный id в patterns.json по сокращённому id из категорий.

    Порядок: точное совпадение, затем префикс hexcasting:, затем единственное
    совпадение по части после двоеточия.

    Raises:
        ValueError: если id не найден или совпадений несколько.
    """
    if short_id in patterns:
        return short_id
    if "hexcasting:" + short_id in patterns:
        return "hexcasting:" + short_id

    matches = [key for key in patterns if key.split(":", 1)[-1] == short_id]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"Паттерн не найден в patterns.json: {short_id}")
    raise ValueError(
        f"Неоднозначный id {short_id}, кандидаты: {', '.join(sorted(matches))}"
    )


def expand_line(line, patterns):
    """Превращает одну строку цепочки в список (направление, сигнатура).

    Raises:
        ValueError: если строку нельзя разобрать или раскрыть.
    """
    text = line.strip()

    match = NUMBER_RE.match(text)
    if match:
        direction, code = n_to_p(int(match.group(1)))
        return [(direction, code)]

    match = VECTOR_RE.match(text)
    if match:
        values = tuple(int(part) for part in match.groups())
        result = []
        for part in vector_pattern(*values):
            pattern_match = PATTERN_LINE_RE.match(part)
            result.append((pattern_match.group(1), pattern_match.group(2)))
        return result

    match = PATTERN_LINE_RE.match(text)
    if match:
        if match.group(1) not in DIRECTIONS:
            raise ValueError(f"Неизвестное направление: {match.group(1)}")
        return [(match.group(1), match.group(2))]

    if "(" in text:
        raise ValueError(f"Паттерны с аргументами не поддерживаются: {text}")

    full_id = resolve_pattern_id(text, patterns)
    entry = patterns[full_id]
    if entry.get("display_only") or not entry.get("signature"):
        raise ValueError(f"У паттерна нет сигнатуры для рендера: {full_id}")
    return [(entry["direction"], entry["signature"])]


def expand_chain(lines, patterns):
    """Раскрывает все строки цепочки. Пустые строки пропускаются.

    Возвращает список (направление, сигнатура) и список ошибок.
    """
    result = []
    errors = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            result.extend(expand_line(line, patterns))
        except ValueError as error:
            errors.append(f"строка {number}: {error}")
    return result, errors


def render_png(patterns, output_path):
    """Рисует список паттернов одним изображением и сохраняет PNG."""
    variants = [
        PatternVariant(direction=direction, angle_sigs=signature)
        for direction, signature in patterns
    ]
    grid = HexGrid(patterns=variants, max_width=50)

    options = GridOptions(
        line_thickness=LINE_THICKNESS,
        pattern_options=GridPatternOptions.Uniform(
            intersections=Intersections.UniformPoints(
                point=Point.Single(
                    marker=Marker(color=MARKER_COLOR, radius=MARKER_RADIUS)
                )
            ),
            lines=Lines.SegmentColors(
                colors=LINE_COLORS,
                triangles=Triangle.BorderStartMatch(
                    ARROW_RADIUS,
                    Marker(color=ARROW_COLOR, radius=ARROW_BORDER_RADIUS),
                ),
                collisions=CollisionOption.ParallelLines(),
            ),
        ),
        center_dot=Point.None_(),
    )

    scale = grid.get_bound_scale(IMAGE_SIZE, options)
    data = bytes(grid.draw_png(scale, options))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as file:
        file.write(data)



def read_input_lines(args):
    """Собирает строки из аргументов и из файла/stdin (-i)."""
    lines = list(args.patterns)
    if args.input is not None:
        if args.input == "-":
            lines.extend(sys.stdin.read().splitlines())
        else:
            with open(args.input, "r", encoding="utf-8") as file:
                lines.extend(file.read().splitlines())
    return lines


def main():
    parser = argparse.ArgumentParser(
        description="Рисует цепочку паттернов Hex Casting в PNG."
    )
    parser.add_argument("patterns", nargs="*", help="строки цепочки в кавычках")
    parser.add_argument(
        "-i", "--input", help="файл со строками цепочки или - для stdin"
    )
    parser.add_argument(
        "-o", "--output", default=DEFAULT_OUTPUT, help="путь к PNG-файлу"
    )
    args = parser.parse_args()

    lines = read_input_lines(args)
    if not any(line.strip() for line in lines):
        print("Нет ни одного паттерна для рисования.", file=sys.stderr)
        sys.exit(1)

    patterns = load_patterns()
    chain, errors = expand_chain(lines, patterns)

    if errors:
        print("Ошибки в цепочке:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    render_png(chain, args.output)
    print(f"Сохранено: {args.output} ({len(chain)} паттернов)")


if __name__ == "__main__":
    main()
