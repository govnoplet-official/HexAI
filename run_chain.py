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
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_DIR = os.path.join(BASE_DIR, "workflow")
RENDERS_DIR = os.path.join(BASE_DIR, "renders")

sys.path.insert(0, WORKFLOW_DIR)

from select_categories import (  # noqa: E402
    CATEGORIES_DIR,
    build_messages as build_category_messages,
    call_api,
    build_supplement_messages,
    find_categories_by_keywords,
    load_api_config,
    load_category_descriptions,
    parse_selection,
)
from build_pattern_chain import (  # noqa: E402
    build_messages as build_chain_messages,
    load_catalog,
    parse_chain,
    parse_need,
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
    chosen, keywords = parse_selection(answer, {name for name, _ in descriptions})
    if keywords:
        print("Ключевые слова (ИИ1):", ", ".join(keywords))
        extra = [name for name in find_categories_by_keywords(keywords) if name not in chosen][:MAX_KEYWORD_EXTRA]
        if extra:
            print("Добавлены по ключевым словам:", ", ".join(extra))
            chosen += extra
    if not chosen:
        sys.exit("ИИ1 не выбрал ни одной категории: запрос не выполним с имеющимися паттернами.")

    print("Категории:", ", ".join(chosen))
    return chosen


DEBUG_LOG = os.path.join(BASE_DIR, "debug_ai2.log")


def debug_log(title, answer):
    """Дописывает сырой ответ ИИ2 в debug_ai2.log (repr, чтобы были видны пустые строки и пробелы)."""
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"=== {datetime.now().isoformat()} | {title}\n{answer!r}\n\n")


MAX_SUPPLEMENTS = 2
MAX_KEYWORD_EXTRA = 3


def stage_supplement_categories(user_request, chosen, missing_keywords, cfg):
    """ИИ1 повторно: добавляет категории под недостающие ключевые слова от ИИ2."""
    descriptions = load_category_descriptions()
    messages = build_supplement_messages(user_request, descriptions, missing_keywords, chosen)
    answer = call_api(messages, cfg["base_url"], cfg["api_keys"], cfg["model"])
    new_chosen, keywords = parse_selection(answer, {name for name, _ in descriptions})

    extra = [name for name in new_chosen if name not in chosen]
    by_keywords = [name for name in find_categories_by_keywords(keywords) if name not in chosen and name not in extra]
    extra += by_keywords[:MAX_KEYWORD_EXTRA]
    return extra


def filter_need_words(words, category_files):
    """Оставляет только слова из NEED, которые встречаются в файлах выбранных категорий."""
    catalog_words = set()
    for name in category_files:
        with open(os.path.join(CATEGORIES_DIR, name), encoding="utf-8") as f:
            catalog_words.update(re.findall(r"[a-z0-9_]+", f.read().lower()))
    return [w for w in words if w.lower() in catalog_words]


def stage_build_chain(user_request, category_files, cfg):
    """ИИ2: возвращает цепочку строк (id, number(N), vector(...)).

    Если ИИ2 не хватает паттернов, он отвечает «NEED: слова». Тогда ИИ1 дополняет категории,
    и ИИ2 собирает цепочку заново (не больше MAX_SUPPLEMENTS раз).
    """
    category_files = list(category_files)
    for attempt in range(MAX_SUPPLEMENTS + 1):
        catalog = load_catalog(category_files)
        if not catalog:
            sys.exit("В выбранных категориях нет паттернов.")

        messages = build_chain_messages(user_request, catalog)
        answer = call_api(messages, cfg["base_url"], cfg["api_keys"], cfg["model"])
        if not answer.strip():
            debug_log(f"ИИ2 попытка {attempt + 1}: пустой ответ, повтор", answer)
            answer = call_api(messages, cfg["base_url"], cfg["api_keys"], cfg["model"])

        missing = parse_need(answer)
        if missing is None:
            break
        debug_log(f"ИИ2 попытка {attempt + 1}, NEED: {missing}", answer)
        missing = filter_need_words(missing, category_files)
        if not missing:
            print("ИИ2 запросил слова, которых нет в каталоге. Повторяю сборку без NEED...")
            messages.append({"role": "assistant", "content": answer})
            messages.append({
                "role": "user",
                "content": "Слова из NEED нет в каталоге. Собери цепочку из имеющихся паттернов, без NEED.",
            })
            answer = call_api(messages, cfg["base_url"], cfg["api_keys"], cfg["model"])
            break
        if attempt == MAX_SUPPLEMENTS:
            sys.exit(f"ИИ2 всё ещё не хватает паттернов после {MAX_SUPPLEMENTS} дозапросов: {missing}")
        print(f"ИИ2 просит паттерны для: {', '.join(missing)}. ИИ1 дополняет категории...")
        extra = stage_supplement_categories(user_request, category_files, missing, cfg)
        if not extra:
            sys.exit(f"ИИ1 не нашёл дополнительных категорий для: {', '.join(missing)}")
        print("Добавлены категории:", ", ".join(extra))
        category_files += extra

    chain, errors = parse_chain(answer, catalog)
    if errors:
        print("Ошибки в цепочке, которую вернул ИИ2:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    if not chain:
        debug_log("ИИ2 пустая цепочка", answer)
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
