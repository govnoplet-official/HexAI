#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


PRIORITY = [
    "stack_manipulation",
    "list_manipulation",
    "reading_writing",
    "patterns",
    "meta",
    "vectors",
    "entities",
    "blocks",
    "inventory",
    "math",
    "effects",
    "physics",
    "combat",
    "strings",
    "sets",
    "ui",
    "world",
    "automation",
    "utilities",
    "misc",
]

RANK = {category: idx for idx, category in enumerate(PRIORITY)}


# Более специфичные правила идут раньше более общих.
REGEX_RULES = [
    # hexcasting: basics / entities / vectors
    (r"^hexcasting:get_caster$", "entities"),
    (r"^hexcasting:entity_pos/", "vectors"),
    (r"^hexcasting:get_entity_look$", "vectors"),
    (r"^hexcasting:get_entity_velocity$", "vectors"),
    (r"^hexcasting:get_entity_height$", "entities"),
    (r"^hexcasting:get_entity(/|$)", "entities"),
    (r"^hexcasting:zone_entity(/|$)", "entities"),

    # hexcasting: constants
    (r"^hexcasting:const/vec/", "vectors"),
    (r"^hexcasting:const/double/", "math"),
    (r"^hexcasting:const/(true|false|null)$", "utilities"),

    # hexcasting: raycast
    (r"^hexcasting:raycast/entity$", "entities"),
    (r"^hexcasting:raycast(/axis)?$", "blocks"),

    # hexcasting: read/write
    (r"^hexcasting:read(/|$)", "reading_writing"),
    (r"^hexcasting:readable(/|$)", "reading_writing"),
    (r"^hexcasting:write(/|$)", "reading_writing"),
    (r"^hexcasting:writable(/|$)", "reading_writing"),

    # hexcasting: meta
    (r"^hexcasting:eval(/|$)", "meta"),
    (r"^hexcasting:for_each$", "meta"),

    # hexcasting: physics/combat
    (r"^hexcasting:add_motion$", "physics"),
    (r"^hexcasting:explode(/fire)?$", "combat"),

    # hexcasting: stack manipulation
    (
        r"^hexcasting:"
        r"(open_paren|close_paren|introjection|retroposition|swizzle|rotate|"
        r"2dup|dup|swap|drop|over|nip|tuck|choose|pack)$",
        "stack_manipulation",
    ),

    # hexcasting: list manipulation
    (
        r"^hexcasting:"
        r"(empty_list|reverse|index|slice|append|prepend|unappend|unpack|"
        r"splat|last_n_list|unique|remove_from|contains)$",
        "list_manipulation",
    ),

    # hexcasting: math
    (
        r"^hexcasting:"
        r"(add|sub|mul|div|pow|abs|mod|floor|ceil|round|sin|cos|tan|"
        r"asin|acos|atan|atan2|log|exp|sqrt|greater|less|eq|not_eq)$",
        "math",
    ),

    # hexcasting: logic/utilities
    (
        r"^hexcasting:"
        r"(and|or|xor|not|bool_coerce|print|reveal)$",
        "utilities",
    ),

    # hextrapats
    (r"^hextrapats:rot_about/", "vectors"),
    (r"^hextrapats:peek/", "list_manipulation"),
    (r"^hextrapats:(splat_set|set_to_list|list_to_set)$", "sets"),
    (r"^hextrapats:swizzle_list$", "list_manipulation"),
    (r"^hextrapats:(haha_ha_one|eno_ah_ahah)$", "vectors"),
    (r"^hextrapats:nocon/bool_coerce$", "utilities"),

    # hexal
    (r"^hexal:wisp/", "meta"),
    (r"^hexal:(factorial|running/(sum|mul))$", "math"),
    (r"^hexal:(armor|toughness)$", "entities"),
    (r"^hexal:light_level$", "world"),
    (r"^hexal:mote/trade$", "inventory"),

    # hexpose
    (r"^hexpose:get_chat$", "ui"),
    (r"^hexpose:block", "blocks"),
    (r"^hexpose:(get_blockstates|query_blockstate|block_map_color)$", "blocks"),
    (r"^hexpose:get_(dimension|einstein)$", "world"),
    (r"^hexpose:env_ambit$", "world"),
    (r"^hexpose:env_(staff|offhand)$", "utilities"),
    (r"^hexpose:env_", "world"),
    (r"^hexpose:(classify|identify)$", "utilities"),
    (r"^hexpose:(get_effects|get_effect)", "effects"),
    (r"^hexpose:villager", "entities"),
    (
        r"^hexpose:"
        r"(cat_variant|creeper_fuse|item_frame_rotation|painting_variant)$",
        "entities",
    ),
    (
        r"^hexpose:"
        r"(item|stack|mainhand|offhand|armor|count|damage|create_stack|get_stack|"
        r"edible|get_hunger|get_saturation|is_meat|is_snack|item_variant)",
        "inventory",
    ),

    # moreiotas
    (r"^moreiotas:string/block/set$", "reading_writing"),
    (r"^moreiotas:string/block/get$", "strings"),
    (r"^moreiotas:string/", "strings"),
    (r"^moreiotas:to_string$", "strings"),
    (r"^moreiotas:item/", "inventory"),
    (r"^moreiotas:matrix/", "math"),
    (r"^moreiotas:type/", "utilities"),
    (r"^moreiotas:get_entity/type$", "entities"),
    (r"^moreiotas:zone_entity/(not_)?type$", "entities"),
    (r"^moreiotas:alt(add|mul|div)$", "math"),

    # ioticblocks
    (r"^ioticblocks:(read|write)/index$", "reading_writing"),

    # lapisworks
    (r"^lapisworks:(empty|visible)", "blocks"),
    (r"^lapisworks:read_", "reading_writing"),
    (r"^lapisworks:", "utilities"),

    # hexical
    (
        r"^hexical:"
        r"(serialize_pattern|deserialize_pattern|draw_pattern|same|similar)$",
        "patterns",
    ),
    (
        r"^hexical:"
        r"(write_charmed|write_grimoire|erase_grimoire|index_grimoire)$",
        "reading_writing",
    ),
    (
        r"^hexical:"
        r"(conjure_speck|iota_speck|kill_specklike|move_specklike|"
        r"rotate_specklike|roll_specklike|size_specklike|"
        r"thickness_specklike|lifetime_specklike)$",
        "ui",
    ),
    (
        r"^hexical:"
        r"(harvest|break_silk|dye|translate_dye|weave_mesh|read_mesh)$",
        "blocks",
    ),
    (
        r"^hexical:"
        r"(item_name|item_lore|index_hopper|get_items?)$",
        "inventory",
    ),
    (
        r"^hexical:"
        r"(magic_missile|llama_spit|snowball|egg|horrible|"
        r"set_lesser_sentinels|get_lesser_sentinels)$",
        "combat",
    ),
    (r"^hexical:(normalize_scroll|age_scroll)$", "utilities"),
    (r"^hexical:glow_scroll$", "ui"),
    (r"^hexical:periwinkle$", "effects"),
    (r"^hexical:wish$", "meta"),
    (r"^hexical:", "utilities"),

    # scryglass / hexmapping / manifestation
    (r"^scryglass:", "ui"),
    (r"^hexmapping:", "ui"),
    (r"^manifestation:clear_stack$", "stack_manipulation"),
    (
        r"^manifestation:"
        r"(create_splinter|destroy_.*splinter|get_splinter_location|"
        r"renew_splinter|saturns_gambit)$",
        "meta",
    ),
    (r"^manifestation:", "ui"),

    # hexweb
    (r"^hexweb:", "utilities"),

    # slate_work
    (r"^slate_work:wave_", "world"),
    (r"^slate_work:", "automation"),

    # hexic
    (r"^hexic:where$", "list_manipulation"),
    (r"^hexic:", "automation"),

    # oneironaut
    (r"^oneironaut:", "automation"),

    # hexflow
    (r"^hexflow:", "meta"),

    # hexthings
    (r"^hexthings:make_range$", "list_manipulation"),
    (r"^hexthings:uiua_", "list_manipulation"),
    (r"^hexthings:", "utilities"),

    # hexdebug
    (r"^hexdebug:", "reading_writing"),

    # focalworks
    (
        r"^focalworks:"
        r"(flip_spellbook|read_spellbook_page|rig_write_index)$",
        "reading_writing",
    ),
    (r"^focalworks:", "inventory"),

    # ephemera
    (r"^ephemera:(removestatus|getstatus)$", "effects"),
    (r"^ephemera:", "entities"),

    # lesser tp
    (r"^lessertp:", "physics"),

    # hexgender
    (r"^hexgender:", "effects"),

    # yaha / dthexcasting / hexssence / hextweaks
    (r"^yaha:", "blocks"),
    (r"^dthexcasting:", "blocks"),
    (r"^hexssence:", "automation"),
    (r"^hextweaks:", "utilities"),
]


def _lower(value) -> str:
    return str(value or "").lower()


def classify(entry: dict, entry_id: str = "") -> str:
    """
    Возвращает новую категорию для поля c.
    """
    eid = _lower(entry_id)

    # 1. Сначала жёсткие правила по id.
    for pattern, category in REGEX_RULES:
        if re.search(pattern, eid):
            return category

    name = _lower(entry.get("n"))
    desc = _lower(entry.get("d"))
    inputs = _lower(entry.get("i"))
    outputs = _lower(entry.get("o"))

    blob = " ".join([eid, name, desc, inputs, outputs])

    scores = defaultdict(int)

    def add(category: str, terms, weight: int = 1):
        for term in terms:
            rx = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
            if re.search(rx, blob):
                scores[category] += weight

    # 2. Эвристики по тексту.
    add(
        "stack_manipulation",
        [
            "swizzle",
            "rotation gambit",
            "duplicate",
            "swap",
            "drop",
            "over",
            "nip",
            "tuck",
            "choose",
            "pack",
            "unpack",
            "introspection",
            "open_paren",
            "close_paren",
            "stack manipulation",
        ],
        weight=8,
    )

    add(
        "list_manipulation",
        [
            "list",
            "index",
            "slice",
            "append",
            "prepend",
            "insert",
            "remove_from",
            "unique",
            "reverse",
            "last_n",
            "splat",
            "make_range",
            "running sum",
            "running product",
            "elements of the list",
            "nth element",
        ],
        weight=5,
    )

    add(
        "reading_writing",
        [
            "read",
            "write",
            "readable",
            "writable",
            "iota holder",
            "splicing table",
            "scribe",
            "chronicler",
            "secretary",
            "compositor",
            "stored in the item",
            "save an iota",
        ],
        weight=8,
    )

    add(
        "patterns",
        [
            "pattern",
            "stroke",
            "draw_pattern",
            "serialize_pattern",
            "deserialize_pattern",
            "similar",
            "compare_pattern",
            "learn_patterns",
            "line-break",
            "comment",
        ],
        weight=6,
    )

    add(
        "meta",
        [
            "eval",
            "for_each",
            "thoth",
            "hermes",
            "iris",
            "jump",
            "gate",
            "circle",
            "spell",
            "intent",
            "execute",
            "cast it as if",
        ],
        weight=8,
    )

    add(
        "vectors",
        [
            "vector",
            "vec",
            "position",
            "pos",
            "eye",
            "foot",
            "look",
            "velocity",
            "direction",
            "normalize",
            "cross product",
            "dot product",
            "components",
            "pitch",
            "yaw",
            "roll",
        ],
        weight=6,
    )

    add(
        "entities",
        [
            "entity",
            "caster",
            "living",
            "animal",
            "monster",
            "player",
            "villager",
            "mob",
            "item entity",
            "dropped item",
            "creature",
        ],
        weight=5,
    )

    add(
        "blocks",
        [
            "block",
            "empty",
            "opaque",
            "harvest",
            "break",
            "blockstate",
            "facet",
            "mine",
            "dye",
        ],
        weight=5,
    )

    add(
        "inventory",
        [
            "item stack",
            "main hand",
            "off hand",
            "inventory",
            "hopper",
            "assembler",
            "trade",
            "craft",
            "slot",
            "held item",
        ],
        weight=6,
    )

    add(
        "math",
        [
            "number",
            "num",
            "addition",
            "subtraction",
            "multiplication",
            "division",
            "exponentiation",
            "modulo",
            "remainder",
            "absolute value",
            "factorial",
            "sum",
            "product",
            "golden ratio",
            "natural logarithm",
            "matrix",
            "scalar",
        ],
        weight=5,
    )

    add(
        "effects",
        [
            "status effect",
            "potion",
            "armor",
            "toughness",
            "light level",
            "hastenature",
            "buff",
            "debuff",
        ],
        weight=6,
    )

    add(
        "physics",
        [
            "motion",
            "impulse",
            "teleport",
            "gravity",
            "drag",
            "ballast",
        ],
        weight=6,
    )

    add(
        "combat",
        [
            "explosion",
            "fireball",
            "damage",
            "projectile",
            "missile",
            "sentinel",
            "wisp",
        ],
        weight=6,
    )

    add(
        "strings",
        [
            "string",
            "text",
            "substring",
            "upper case",
            "lower case",
            "concatenate",
            "character",
        ],
        weight=5,
    )

    add(
        "sets",
        [
            "set",
            "unordered",
            "unique elements",
        ],
        weight=5,
    )

    add(
        "ui",
        [
            "icon",
            "marker",
            "map",
            "input field",
            "slider",
            "checkbox",
            "dropdown",
            "scryglass",
            "manifestation",
            "display",
        ],
        weight=5,
    )

    add(
        "world",
        [
            "dimension",
            "time",
            "weather",
            "ambit",
            "env",
            "day",
            "night",
            "wave",
        ],
        weight=4,
    )

    add(
        "automation",
        [
            "assembler",
            "macro",
            "pocket simulator",
            "spell imprinter",
            "directrix",
            "locus",
            "great work",
            "engine",
            "rotor",
        ],
        weight=5,
    )

    add(
        "utilities",
        [
            "const",
            "print",
            "reveal",
            "classify",
            "identify",
            "null",
            "true",
            "false",
            "empty list",
            "comment",
            "line break",
            "type",
        ],
        weight=3,
    )

    # 3. Небольшие бусты по типу выхода.
    if re.search(r"(?<!\w)vector(?!\w)", outputs) and scores["vectors"]:
        scores["vectors"] += 10

    if re.search(r"(?<!\w)entity(?!\w)", outputs) and scores["entities"]:
        scores["entities"] += 10

    if re.search(r"(?<!\w)list(?!\w)", outputs) and scores["list_manipulation"]:
        scores["list_manipulation"] += 10

    if "item stack" in blob or "itemtype" in blob:
        scores["inventory"] += 5

    if not scores:
        return "utilities"

    # При равных очках выбираем категорию с более высоким приоритетом.
    return max(
        scores.keys(),
        key=lambda category: (scores[category], -RANK.get(category, 999)),
    )


def transform(node, key=None):
    """
    Рекурсивно обходит JSON и заменяет c у объектов-паттернов.
    Поддерживает оба варианта:
      1) {"hexcasting:get_caster": {"n": ..., "c": ..., "d": ...}}
      2) [{"n": ..., "c": ..., "d": ...}, ...]
    """
    if isinstance(node, dict):
        # Если это похоже на запись паттерна, переоцениваем c.
        if "c" in node and any(field in node for field in ("n", "d", "i", "o")):
            old_c = node.get("c")

            # Раскомментируй, если хочешь сохранить оригинальное название мода:
            # node["mod"] = old_c

            node["c"] = classify(node, key or "")
            return node

        # Иначе идём внутрь словаря.
        for child_key, child_value in list(node.items()):
            node[child_key] = transform(child_value, child_key)
        return node

    if isinstance(node, list):
        return [transform(item, key) for item in node]

    return node


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python categorize_hex.py input.json [output.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(
        src.stem + ".categorized.json"
    )

    try:
        data = json.loads(src.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        print(
            "Если в файле есть обрезки вида ..., сначала убери их или пришли полный JSON.",
            file=sys.stderr,
        )
        sys.exit(2)

    data = transform(data)

    dst.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"OK: {dst}")


if __name__ == "__main__":
    main()