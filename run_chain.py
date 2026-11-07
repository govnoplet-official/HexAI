"""
Полный конвейер Hex Casting: запрос пользователя -> PNG.

Этапы:
1. ИИ1 (workflow/select_categories.py) выбирает категории по запросу.
2. ИИ2 (workflow/build_pattern_chain.py) собирает цепочку паттернов из этих категорий.
3. Замена id на паттерны из intermediary/patterns.json, генерация чисел (number(N))
   и векторов (vector(x, y, z)) - workflow/render_pattern.py.
4. Рендер цепочки в PNG в папке renders/.

Использование (из корня проекта, интерпретатором из venv):
    venv\\Scripts\\python.exe run_chain.py

Скрипт ждёт запрос в консоли. Настройки API берутся из config.json.
"""

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_DIR = os.path.join(BASE_DIR, "workflow")
RENDERS_DIR = os.path.join(BASE_DIR, "renders")

sys.path.insert(0, WORKFLOW_DIR)

from select_categories import (  # noqa: E402
    build_messages as build_category_messages,
    call_api,
    load_api_config,
    load_category_descriptions,
    parse_categories,
)
from build_pattern_chain import (  # noqa: E402
    build_messages as build_chain_messages,
    load_catalog,
    parse_chain,
)
from render_pattern import expand_chain, load_patterns, render_png  # noqa: E402


def read_request():
    """Ждёт запрос пользователя в консоли."""
    try:
        request = input("Введите запрос: ").strip()
    except EOFError:
        sys.exit("Запрос не получен.")
    if not request:
        sys.exit("Запрос пуст.")
    return request


def stage_select_categories(user_request, cfg):
    """ИИ1: возвращает список имён файлов категорий."""
    descriptions = load_category_descriptions()
    if not descriptions:
        sys.exit("Нет файлов категорий с полем _description в categories_enabled/.")

    messages = build_category_messages(user_request, descriptions)
    answer = call_api(messages, cfg["base_url"], cfg["api_keys"], cfg["model"])
    chosen = parse_categories(answer, {name for name, _ in descriptions})
    if not chosen:
        sys.exit("ИИ1 не выбрал ни одной категории: запрос не выполним с имеющимися паттернами.")

    print("Категории:", ", ".join(chosen))
    return chosen


def stage_build_chain(user_request, category_files, cfg):
    """ИИ2: возвращает цепочку строк (id, number(N), vector(...))."""
    catalog = load_catalog(category_files)
    if not catalog:
        sys.exit("В выбранных категориях нет паттернов.")

    messages = build_chain_messages(user_request, catalog)
    answer = call_api(messages, cfg["base_url"], cfg["api_keys"], cfg["model"])
    chain, errors = parse_chain(answer, catalog)
    if errors:
        print("Ошибки в цепочке, которую вернул ИИ2:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    if not chain:
        sys.exit("ИИ2 не вернул ни одного паттерна.")

    print("Цепочка (ИИ2):")
    for line in chain:
        print(f"  {line}")
    return chain


def stage_expand(chain):
    """Заменяет id на направления и сигнатуры, раскрывает числа и векторы."""
    patterns = load_patterns()
    expanded, errors = expand_chain(chain, patterns)
    if errors:
        print("Ошибки при замене паттернов:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    return expanded


def stage_render(expanded):
    """Рисует цепочку в PNG и возвращает путь к файлу."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(RENDERS_DIR, f"chain_{timestamp}.png")
    render_png(expanded, output_path)
    return output_path


def open_image(path):
    """Открывает PNG в программе по умолчанию (Windows). На других системах только выводит путь."""
    if sys.platform == "win32":
        os.startfile(path)
    else:
        print(f"Откройте файл вручную: {path}")


def main():
    user_request = read_request()
    cfg = load_api_config()

    print("\n[1/4] Выбор категорий (ИИ1)...")
    category_files = stage_select_categories(user_request, cfg)

    print("\n[2/4] Сборка цепочки паттернов (ИИ2)...")
    chain = stage_build_chain(user_request, category_files, cfg)

    print("\n[3/4] Замена id, генерация чисел и векторов...")
    expanded = stage_expand(chain)
    print(f"Итого паттернов для рендера: {len(expanded)}")

    print("\n[4/4] Рендер...")
    output_path = stage_render(expanded)
    print(f"Готово: {output_path}")
    open_image(output_path)


if __name__ == "__main__":
    main()
