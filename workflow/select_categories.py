"""
Скрипт 1: выбор категорий паттернов с помощью ИИ-модели.

Модель получает запрос пользователя, свою задачу и описания категорий
(поле "_description" каждого файла из categories_enabled/).
На выходе — список имён файлов категорий (JSON-массив).

Использование:
    python select_categories.py "текст запроса"
    python select_categories.py "текст запроса" --dry-run   (только показать промпт)

Настройки API берутся из config.json (см. api_config.py).
Запрос к API совместим с OpenAI Chat Completions: {base_url}/chat/completions.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "preparation"))

from api_config import load_api_config

CATEGORIES_DIR = os.path.join(BASE_DIR, "categories_enabled")
MODEL_NAME = "gpt-4o-mini"
TIMEOUT_SEC = 120

TASK_TEXT = """\
Ты — отборщик категорий в конвейере, который собирает заклинания для игры Minecraft с модом Hex Casting.

КОНТЕКСТ
- В Hex Casting заклинание — это последовательность «паттернов». Каждый паттерн выполняет одну операцию \
над стеком (стек — это список значений, называемых «иотами»). Паттерны бывают для чисел, векторов, \
списков, сущностей, блоков, текста и т.д.
- Все доступные паттерны разбиты по категориям, и каждая категория хранится в отдельном файле \
(например, math.json, vectors.json). Ниже тебе дан список таких категорий с кратким описанием \
и примерами применения.
- Твоя работа — определить, из каких категорий нужно взять паттерны, чтобы решить запрос пользователя. \
Следующий шаг конвейера (другая модель) будет выбирать конкретные паттерны только внутри \
категорий, которые передашь ты. Если категорию не передать, её паттерны в заклинании не появятся, \
поэтому пропуск нужной категории — серьёзная ошибка.

ОГРАНИЧЕНИЯ
- У тебя нет доступа к интернету и веб-поиску. Решай только по описаниям категорий, которые даны в сообщении. \
Не придумывай категории, которых нет в списке, и не опирайся на знания о Hex Casting, если они \
противоречат описаниям.
- Имена файлов бери только из списка, точно как написано после «##». Не меняй регистр, не добавляй \
пути и не сокращай.

КАК ВЫБИРАТЬ
1. Разбей запрос пользователя на шаги: что нужно получить, что посчитать, с чем взаимодействовать \
(сущности, блоки, предметы, текст, списки и т.д.), что нужно сохранить или вывести.
2. Для каждого шага найди категорию, чьё описание или «Применение» явно под него подходит.
3. Включай категорию, если без неё хотя бы один шаг не выполнить. Если шаг неоднозначен, но категория \
может быть нужна, включи её.
4. Не включай категории «на всякий случай», если ни один шаг их не требует.
5. Если запрос не относится к Hex Casting или ни одна категория не подходит, верни пустой массив [].
6. Категории могут дублировать друг друга по смыслу. Тогда выбери ту, чьё описание точнее совпадает \
с задачей, а не все подряд.

ФОРМАТ ОТВЕТА
- Только JSON-массив строк: имена файлов из списка, без повторов.
- Никакого текста до или после массива, никаких пояснений, никаких блоков кода с тремя обратными кавычками.
- Порядок элементов не важен.

ПРИМЕРЫ
Запрос: «Сложить два числа и вывести результат».
Ответ: ["math.json", "utilities.json"]

Запрос: «Получить позицию глаз ближайшей сущности и сдвинуть её на один блок вверх».
Ответ: ["entities.json", "vectors.json"]

Запрос: «Напиши стихотворение про кота».
Ответ: []\
"""


def load_category_descriptions():
    """Возвращает список (имя_файла, описание) для всех файлов с _description."""
    result = []
    for name in sorted(os.listdir(CATEGORIES_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CATEGORIES_DIR, name)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        desc = raw.get("_description")
        if not isinstance(desc, dict):
            continue
        result.append((name, desc))
    return result


def build_categories_block(descriptions):
    lines = []
    for name, desc in descriptions:
        lines.append(f"## {name}")
        lines.append(f"Описание: {desc.get('summary', '').strip()}")
        use_cases = desc.get("use_cases", [])
        if use_cases:
            lines.append("Применение:")
            lines.extend(f"- {u}" for u in use_cases)
        lines.append("")
    return "\n".join(lines)


def build_messages(user_request, descriptions):
    user_content = (
        "Категории:\n\n"
        f"{build_categories_block(descriptions)}\n"
        f"Запрос пользователя:\n{user_request.strip()}"
    )
    return [
        {"role": "system", "content": TASK_TEXT},
        {"role": "user", "content": user_content},
    ]


def call_api(messages, base_url, api_keys):
    """Отправляет запрос; при ошибке авторизации или лимита переходит к следующему ключу."""
    body = json.dumps({
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0,
    }).encode("utf-8")
    last_error = None

    for key in api_keys:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}"
            if e.code not in (401, 403, 429):
                break
        except urllib.error.URLError as e:
            last_error = f"Сеть: {e.reason}"
            break
        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
            # Таймаут сокета, некорректный JSON или неожиданная структура ответа
            last_error = f"Ошибка обработки ответа API: {e!r}"
            break

    sys.exit(f"Запрос к API не удался. {last_error}")


def parse_categories(answer, valid_names):
    """Достаёт JSON-массив из ответа модели и оставляет только существующие файлы."""
    match = re.search(r"\[.*\]", answer, re.DOTALL)
    if not match:
        sys.exit(f"Модель не вернула JSON-массив. Ответ:\n{answer}")
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        sys.exit(f"Не удалось разобрать JSON из ответа модели:\n{answer}")
    if not isinstance(items, list):
        sys.exit(f"Ответ модели не является JSON-массивом:\n{answer}")

    chosen = []
    unknown = []
    for item in items:
        if isinstance(item, str) and item in valid_names:
            if item not in chosen:
                chosen.append(item)
        else:
            # repr, т.к. элемент может быть объектом/массивом (не хешируется)
            unknown.append(item)
    if unknown:
        print(f"Предупреждение: модель вернула неизвестные категории, пропущены: {unknown}", file=sys.stderr)
    return chosen


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in sys.argv[1:]
    if not args:
        sys.exit("Укажите запрос пользователя в аргументах командной строки.")
    user_request = " ".join(args)

    descriptions = load_category_descriptions()
    if not descriptions:
        sys.exit(f"В {CATEGORIES_DIR} нет файлов с полем _description.")
    messages = build_messages(user_request, descriptions)

    if dry_run:
        print(messages[0]["content"])
        print("\n---\n")
        print(messages[1]["content"])
        return

    cfg = load_api_config()
    answer = call_api(messages, cfg["base_url"], cfg["api_keys"])
    chosen = parse_categories(answer, {name for name, _ in descriptions})

    print(json.dumps(chosen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
