"""
n_to_p(n) - возвращает направление и Hex Casting паттерн для числа n.

Использование из другого файла, лежащего в той же папке:
    from n_to_p import n_to_p
    direction, pattern = n_to_p(42)
    print(direction, pattern)  # SOUTH_EAST aqaaeawa

Запускать нужно интерпретатором из venv, где установлен hexnumgen.
"""

from datetime import timedelta

from hexnumgen import AStarOptions, generate_number_pattern

TIMEOUT_SECONDS = 10


def n_to_p(n: int) -> tuple[str, str]:
    """Возвращает (направление, паттерн) Hex Casting для числа n.

    Направление - это начальное направление паттерна (например, SOUTH_EAST).

    Raises:
        TypeError: если n не целое число.
        ValueError: если паттерн для числа не найден.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n должно быть целым числом")

    result = generate_number_pattern(
        n,
        trim_larger=True,
        allow_fractions=False,
        options=AStarOptions(timeout=timedelta(seconds=TIMEOUT_SECONDS)),
    )

    if result is None:
        raise ValueError(f"Не удалось найти паттерн для числа {n}")

    return result.direction, result.pattern
