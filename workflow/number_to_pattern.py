"""
Принимает число и выводит Hex Casting паттерн, который создаёт это число.

Использование:
    python number_to_pattern.py <число>

Пример:
    python number_to_pattern.py 42
"""

import sys
from datetime import timedelta

from hexnumgen import AStarOptions, generate_number_pattern

TIMEOUT_SECONDS = 10


def main():
    if len(sys.argv) != 2:
        print("Использование: python number_to_pattern.py <число>", file=sys.stderr)
        sys.exit(1)

    try:
        target = int(sys.argv[1])
    except ValueError:
        print("Аргумент должен быть целым числом.", file=sys.stderr)
        sys.exit(1)

    result = generate_number_pattern(
        target,
        trim_larger=True,
        allow_fractions=False,
        options=AStarOptions(timeout=timedelta(seconds=TIMEOUT_SECONDS)),
    )

    if result is None:
        print(f"Не удалось найти паттерн для числа {target}.", file=sys.stderr)
        sys.exit(1)

    print(f"Число: {target}")
    print(f"Направление: {result.direction}")
    print(f"Паттерн: {result.pattern}")


if __name__ == "__main__":
    main()
