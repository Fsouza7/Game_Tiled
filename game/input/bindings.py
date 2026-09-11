"""Rebindable gameplay keys.

Mouse, hotbar 1-9, Esc, and F3-F11 stay hardcoded -- those are either
not keys, or they would brick pause/debug/hotbar if a player rebound
them and then couldn't get into Settings to undo it. Arrow keys still
move left/right *unless* that arrow is already claimed by some binding,
so WASD players keep the arrows as a fallback and a rebound Left-arrow
inventory key doesn't also walk.
"""
from typing import Dict, Iterable, Optional

import pygame


# (action_id, Settings-row label) -- order is the Settings panel order.
BINDABLE_ACTIONS = (
    ("move_left", "Move Left"),
    ("move_right", "Move Right"),
    ("jump", "Jump"),
    ("inventory", "Inventory"),
    ("use_accessory", "Use Accessory"),
    ("crafting", "Crafting"),
    ("skills", "Skills"),
    ("map", "Map"),
    ("interact", "Talk / Interact"),
    ("eat", "Eat"),
    ("summon_boss", "Summon Boss"),
)

DEFAULT_BINDINGS: Dict[str, int] = {
    "move_left": pygame.K_a,
    "move_right": pygame.K_d,
    "jump": pygame.K_SPACE,
    "inventory": pygame.K_i,
    "use_accessory": pygame.K_e,
    "crafting": pygame.K_c,
    "skills": pygame.K_k,
    "map": pygame.K_m,
    "interact": pygame.K_t,
    "eat": pygame.K_f,
    "summon_boss": pygame.K_g,
}

_RESERVED_KEYS = frozenset(
    {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER}
    | {pygame.K_F1 + i for i in range(12)}
    | {pygame.K_1 + i for i in range(9)}
)

_DISPLAY_ALIASES = {
    pygame.K_SPACE: "Space",
    pygame.K_LEFT: "Left",
    pygame.K_RIGHT: "Right",
    pygame.K_UP: "Up",
    pygame.K_DOWN: "Down",
    pygame.K_TAB: "Tab",
    pygame.K_LSHIFT: "LShift",
    pygame.K_RSHIFT: "RShift",
    pygame.K_LCTRL: "LCtrl",
    pygame.K_RCTRL: "RCtrl",
    pygame.K_LALT: "LAlt",
    pygame.K_RALT: "RAlt",
    pygame.K_BACKSPACE: "Backspace",
    pygame.K_CAPSLOCK: "Caps",
}

_NAME_ALIASES = {
    "space": pygame.K_SPACE,
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "up": pygame.K_UP,
    "down": pygame.K_DOWN,
    "tab": pygame.K_TAB,
    "lshift": pygame.K_LSHIFT,
    "rshift": pygame.K_RSHIFT,
    "left shift": pygame.K_LSHIFT,
    "right shift": pygame.K_RSHIFT,
    "lctrl": pygame.K_LCTRL,
    "rctrl": pygame.K_RCTRL,
    "left ctrl": pygame.K_LCTRL,
    "right ctrl": pygame.K_RCTRL,
    "lalt": pygame.K_LALT,
    "ralt": pygame.K_RALT,
    "backspace": pygame.K_BACKSPACE,
}


def key_from_name(name: str) -> Optional[int]:
    text = name.strip().lower()
    if not text:
        return None
    if text in _NAME_ALIASES:
        return _NAME_ALIASES[text]
    if len(text) == 1 and "a" <= text <= "z":
        return pygame.K_a + (ord(text) - ord("a"))
    if len(text) == 1 and "0" <= text <= "9":
        return pygame.K_0 + (ord(text) - ord("0"))
    try:
        if not pygame.get_init():
            return None
        return pygame.key.key_code(text)
    except (ValueError, KeyError, pygame.error):
        return None


def key_to_name(key: int) -> str:
    if pygame.K_a <= key <= pygame.K_z:
        return chr(ord("a") + (key - pygame.K_a))
    if pygame.K_0 <= key <= pygame.K_9:
        return chr(ord("0") + (key - pygame.K_0))
    for name, bound in _NAME_ALIASES.items():
        if bound == key:
            return name
    try:
        return pygame.key.name(key)
    except Exception:
        return str(key)


def key_display_name(key: int) -> str:
    if key in _DISPLAY_ALIASES:
        return _DISPLAY_ALIASES[key]
    name = pygame.key.name(key)
    if len(name) == 1:
        return name.upper()
    return name.title()


def is_reserved_key(key: int) -> bool:
    return key in _RESERVED_KEYS


def parse_bindings(data) -> Dict[str, int]:
    """Merges a JSON-ish dict (action -> key name or int) onto defaults.
    Unknown actions/names are ignored so a hand-edited file can't drop
    a required action or crash boot."""
    result = dict(DEFAULT_BINDINGS)
    if not isinstance(data, dict):
        return result
    for action, value in data.items():
        if action not in DEFAULT_BINDINGS:
            continue
        if isinstance(value, int):
            result[action] = value
            continue
        key = key_from_name(str(value))
        if key is not None:
            result[action] = key
    return result


def serialize_bindings(bindings: Dict[str, int]) -> Dict[str, str]:
    return {action: key_to_name(key) for action, key in bindings.items() if action in DEFAULT_BINDINGS}


def bound_key(prefs, action: str) -> int:
    bindings = getattr(prefs, "bindings", None) if prefs is not None else None
    if isinstance(bindings, dict) and action in bindings:
        return bindings[action]
    return DEFAULT_BINDINGS[action]


def action_using_key(bindings: Dict[str, int], key: int) -> Optional[str]:
    for action, bound in bindings.items():
        if bound == key:
            return action
    return None


def extra_arrow_held(keys, prefs, action: str) -> bool:
    """True when the matching arrow is held and isn't anybody's binding."""
    extra = pygame.K_LEFT if action == "move_left" else pygame.K_RIGHT
    if not keys[extra]:
        return False
    bindings = getattr(prefs, "bindings", None) if prefs is not None else None
    claimed: Iterable[int] = bindings.values() if isinstance(bindings, dict) else DEFAULT_BINDINGS.values()
    return extra not in claimed
