"""
Скрипт 2: сборка цепочки паттернов Hex Casting моделью.

Модель получает запрос пользователя, инструкции и JSON-файлы категорий,
которые выбрала модель из скрипта 1 (select_categories.py).
На выходе — цепочка паттернов: одна строка на паттерн, в порядке выполнения.
Формат строки: "id" или "id(аргументы)". Аргументы пишутся только для паттернов,
у которых в категориях есть поле "u" (сейчас это special handlers, например mask).

Использование:
    python build_pattern_chain.py "текст запроса" --categories math.json utilities.json
    python build_pattern_chain.py "текст запроса" --categories math.json --dry-run

Ответ модели проверяется: неизвестные id и лишние аргументы выводятся как ошибки,
код выхода при ошибках — 1.
"""

import json
import os
import re
import sys

WORKFLOW_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(WORKFLOW_DIR)
CATEGORIES_DIR = os.path.join(BASE_DIR, "categories_enabled")

sys.path.insert(0, WORKFLOW_DIR)
from select_categories import call_api, load_api_config  # noqa: E402

TASK_TEXT = """\
Ты — сборщик заклинаний для игры Minecraft с модом Hex Casting. По запросу пользователя ты составляешь \
цепочку паттернов, которая его выполняет.

КОНТЕКСТ
- Заклинание — это программа, которая выполняется по порядку, строка за строкой. Вычисления идут через \
стек: это упорядоченный список значений, у которого есть только верхушка. Новое значение кладётся \
сверху, паттерн берёт значения с верхушки. Например, если на стеке [1, 2] (2 сверху), паттерн add \
снимает 2 и 1 и кладёт 3.
- Значения на стеке называются «иотами». Иота может быть числом, вектором (тройка координат), \
списком, сущностью в мире, блоком, текстом, паттерном и т.д.
- Каждый паттерн читает свои входы с верхушки стека и кладёт на стек свои выходы. Во входах и выходах \
в каталоге указан порядок: например, «num, num» означает, что сверху лежит второе число, а под ним первое, \
и паттерн использует их в этом порядке.
- Тебе дан каталог доступных паттернов. Каждый паттерн описан блоком, который начинается с \
строки «## <id>». Используй только эти паттерны и литералы, описанные ниже.
- Для каждого паттерна указаны: название, описание, входы (что паттерн берёт со стека) и выходы \
(что кладёт на стек). Значение «-» означает, что входов или выходов нет.

ЧИСЛА
- Число на стек кладётся литералом «number(N)», где N — целое или дробное число. Например, number(24) \
или number(-3). Литерал number(...) не нужно искать в каталоге: он всегда доступен.
- Каждое число, которое нужно использовать, должно сначала появиться на стеке через такой литерал \
(или через результат другого паттерна).
- Не вычисляй числа в уме и не записывай результат вычисления как литерал. Если нужна сумма, \
ставь число, число и add.

ВЕКТОРЫ
- Вектор (тройка координат x, y, z) кладётся на стек литералом «vector(x, y, z)», например \
vector(0, 1, 0). Все три компонента — числа, записанные через литерал number(...) не нужно: \
просто пиши числа внутри скобок. Литерал vector(...) тоже всегда доступен и не ищется в каталоге.
- Вектор можно собрать и паттерном construct_vec из трёх чисел на стеке (число x, число y, число z; \
z сверху). Это удобно, когда компоненты сами получены другими паттернами. Для вектора из известных \
чисел проще и короче использовать литерал vector(x, y, z).

ФОРМАТ ОТВЕТА
- Одна строка на один паттерн, в порядке выполнения.
- Строка имеет вид «id» или «id(аргументы)».
- id пишется точно так, как после «## » в каталоге. Не меняй регистр, не добавляй пространство имён, \
не придумывай новые id.
- Аргументы пишутся в скобках, только если в описании паттерна есть строка «Аргументы:». \
Формат аргументов и их смысл описаны в этой строке. Для паттернов без «Аргументы:» скобки не ставь.
- Никакого текста до или после цепочки, никаких пояснений, нумерации, пустых строк между паттернами, \
markdown и блоков кода с тремя обратными кавычками.

КАК СОСТАВЛЯТЬ ЦЕПОЧКУ
1. Разбей запрос на шаги: какие исходные значения нужны, что с ними сделать, что оставить на стеке \
в конце.
2. Для каждого шага выбери паттерны из каталога. Проверяй, что на стеке есть нужные входы в этот момент, \
и что выходы предыдущих паттернов соответствуют входам следующих.
3. Если в запросе есть число или значение, которого нет в каталоге, не придумывай паттерн для него. \
Пропусти такой шаг и не выводи его в цепочке.
4. Не добавляй паттерны, которые не нужны для запроса.
5. Если запрос нельзя выполнить с имеющимися паттернами, верни пустой ответ (ни одной строки).

ПРИМЕРЫ
Примеры показывают формат. Строки после «Ответ:» — это то, что ты выводишь целиком, без самой метки.

Запрос: сложить 5 и 28
Ответ:
number(5)
number(28)
add

Запрос: получить позицию глаз сущности, на которую я смотрю, и сдвинуть её на один блок вверх
Ответ:
raycast/entity
entity_pos/eye
vector(0, 1, 0)
add

Запрос: из стека оставить элементы 1, 2 и 4 (исходный стек: 1, 2, 3, 4, 5)
Ответ:
mask(11010)

Запрос: напиши стихотворение про кота
Ответ:
(пусто: в каталоге нет паттернов для этого)\

Запрос: сломать блок, на который я смотрю
Ответ:
get_caster
entity_pos/eye
get_caster
get_entity_look
raycast
break_block

"""


def load_catalog(category_files):
    """Собирает каталог паттернов из выбранных файлов: id -> поля паттерна."""
    catalog = {}
    for name in category_files:
        path = os.path.join(CATEGORIES_DIR, name)
        if not os.path.exists(path):
            sys.exit(f"Файл категории не найден: {path}")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for key, entry in raw.items():
            if key.startswith("_") or not isinstance(entry, dict):
                continue
            catalog[key] = entry
    return catalog


def format_pattern(pid, entry):
    lines = [f"## {pid}"]
    lines.append(f"Название: {entry.get('n', '-')}")
    lines.append(f"Описание: {str(entry.get('d', '-')).strip()}")
    lines.append(f"Входы: {entry.get('i', '-')}")
    lines.append(f"Выходы: {entry.get('o', '-')}")
    if entry.get("u"):
        lines.append(f"Аргументы: {entry['u'].strip()}")
    return "\n".join(lines)


def build_messages(user_request, catalog):
    catalog_text = "\n\n".join(format_pattern(pid, e) for pid, e in catalog.items())
    user_content = (
        f"Каталог паттернов:\n\n{catalog_text}\n\n"
        f"Запрос пользователя:\n{user_request.strip()}"
    )
    return [
        {"role": "system", "content": TASK_TEXT},
        {"role": "user", "content": user_content},
    ]



LINE_RE = re.compile(r"^([A-Za-z0-9_./:\-]+)(?:\((.*)\))?$")
NUMBER_LITERAL = "number"
NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
VECTOR_LITERAL = "vector"
VECTOR_RE = re.compile(r"^\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*$")


def parse_chain(answer, catalog):
    """Разбирает ответ модели и проверяет каждую строку. Возвращает (цепочка, ошибки)."""
    chain = []
    errors = []
    for raw in answer.splitlines():
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        match = LINE_RE.match(line)
        if not match:
            errors.append(f"строка не похожа на паттерн: {line!r}")
            continue
        pid, args = match.group(1), match.group(2)
        if pid == VECTOR_LITERAL:
            if args is None or not VECTOR_RE.match(args):
                errors.append(f"литерал вектор должен быть vector(x, y, z) с тремя числами, получено: {line}")
            else:
                chain.append(line)
            continue
        if pid == NUMBER_LITERAL:
            if args is None or not NUMBER_RE.match(args.strip()):
                errors.append(f"литерал число должен быть number(N), получено: {line}")
            else:
                chain.append(line)
            continue
        if pid not in catalog:
            errors.append(f"id нет в выбранных категориях: {pid}")
            continue
        entry = catalog[pid]
        if args is not None and not entry.get("u"):
            errors.append(f"паттерн {pid} не принимает аргументы: {line}")
            continue
        if args is not None and not args.strip():
            errors.append(f"пустые аргументы у {pid}: {line}")
            continue
        chain.append(line)
    return chain, errors


def main():
    argv = sys.argv[1:]
    dry_run = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]

    if "--categories" not in argv:
        sys.exit("Укажите категории: --categories math.json utilities.json")
    idx = argv.index("--categories")
    request_parts = argv[:idx]
    category_files = argv[idx + 1:]

    if not request_parts:
        sys.exit("Укажите запрос пользователя перед --categories.")
    if not category_files:
        sys.exit("После --categories укажите хотя бы один файл категории.")

    user_request = " ".join(request_parts)
    catalog = load_catalog(category_files)
    if not catalog:
        sys.exit("В выбранных файлах нет паттернов.")

    messages = build_messages(user_request, catalog)

    if dry_run:
        print(messages[0]["content"])
        print("\n---\n")
        print(messages[1]["content"])
        return

    cfg = load_api_config()
    answer = call_api(messages, cfg["base_url"], cfg["api_keys"])
    chain, errors = parse_chain(answer, catalog)

    if errors:
        print("Ошибки в ответе модели:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)

    print("\n".join(chain))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
