"""
Принимает три числа (x, y, z) и выводит Hex Casting паттерн литерала вектора.

Оси и их фиксированные направления и базовые буквы:
- x: направление SOUTH_WEST, базовая буква "a"
- y: направление EAST, базовая буква "w"
- z: направление NORTH_EAST, базовая буква "d"

Для каждого значения вызывается n_to_p(значение) -> (направление, код).
Направление из n_to_p отбрасывается. Если оно SOUTH_EAST, к коду спереди добавляется "e",
если NORTH_EAST, то "q". Итоговый код компонента = базовая буква + префикс + код из n_to_p.

Правила вывода:
- Ровно один ненулевой компонент: выводится только он, в виде "НАПРАВЛЕНИЕ код".
  Пример: (5, 0, 0) -> SOUTH_WEST aeaqaaq
- Больше одного ненулевого компонента: выводятся x, y, add, z, add.
  Компонент выводится в виде "НАПРАВЛЕНИЕ код", add выводится строкой "NORTH_EAST waaw".
- Нулевой вектор (0, 0, 0) выводится как фиксированная строка "SOUTH_WEST aeaqaa".

Использование:
    python vector_to_pattern.py <x> <y> <z>

Пример:
    python vector_to_pattern.py 5 0 0

Запускать нужно интерпретатором из venv, где установлен hexnumgen.
"""

import sys

from n_to_p import n_to_p

AXES = (
    ("x", "SOUTH_WEST", "a"),
    ("y", "EAST", "w"),
    ("z", "NORTH_EAST", "d"),
)
PREFIX_BY_DIRECTION = {"SOUTH_EAST": "e", "NORTH_EAST": "q"}
ADD = "NORTH_EAST waaw"
ZERO_VECTOR = "SOUTH_WEST aeaqaa"


def component_pattern(name, value, direction, base):
    """Возвращает строку 'НАПРАВЛЕНИЕ код' для одного компонента вектора."""
    number_direction, code = n_to_p(value)
    prefix = PREFIX_BY_DIRECTION.get(number_direction)
    if prefix is None:
        raise ValueError(
            f"Для компонента {name}={value} неожиданное направление {number_direction}: "
            "ожидалось SOUTH_EAST или NORTH_EAST"
        )
    return f"{direction} {base + prefix + code}"


def vector_pattern(x, y, z):
    """Возвращает список строк паттерна для вектора (x, y, z)."""
    values = (x, y, z)
    nonzero = [index for index, value in enumerate(values) if value != 0]

    if not nonzero:
        return [ZERO_VECTOR]

    if len(nonzero) == 1:
        index = nonzero[0]
        name, direction, base = AXES[index]
        return [component_pattern(name, values[index], direction, base)]

    parts = []
    for index in (0, 1):
        name, direction, base = AXES[index]
        parts.append(component_pattern(name, values[index], direction, base))
    parts.append(ADD)
    name, direction, base = AXES[2]
    parts.append(component_pattern(name, values[2], direction, base))
    parts.append(ADD)
    return parts


def main():
    if len(sys.argv) != 4:
        print("Использование: python vector_to_pattern.py <x> <y> <z>", file=sys.stderr)
        sys.exit(1)

    try:
        x, y, z = (int(arg) for arg in sys.argv[1:])
    except ValueError:
        print("Компоненты вектора должны быть целыми числами.", file=sys.stderr)
        sys.exit(1)

    try:
        lines = vector_pattern(x, y, z)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)

    print("\n".join(lines))


if __name__ == "__main__":
    main()
