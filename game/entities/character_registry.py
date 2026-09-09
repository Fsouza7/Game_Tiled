"""Central, data-driven table of every playable character skin.

The asset pack has 4 interchangeable character folders (same frame size,
same animation filenames: idle/run/jump/fall) -- see README "Art reuse".
Adding a character means adding one entry here plus a matching folder
under assets/MainCharacters/ with the same 4 file names; no other file
needs to change (Renderer loads every registered character's animations
up front, GameApp's character-select screen lists whatever is registered).
"""
import os
from dataclasses import dataclass
from typing import Dict, List

_CHARACTERS_DIR = os.path.join("assets", "MainCharacters")


@dataclass(frozen=True)
class CharacterDef:
    id: str
    name: str
    asset_dir: str  # folder under assets/MainCharacters/


_CHARACTERS: Dict[str, CharacterDef] = {}


def _register(character: CharacterDef) -> None:
    if character.id in _CHARACTERS:
        raise ValueError(f"Duplicate character id {character.id}")
    _CHARACTERS[character.id] = character


_register(CharacterDef(id="ninja_frog", name="Ninja Frog", asset_dir=os.path.join(_CHARACTERS_DIR, "NinjaFrog")))
_register(CharacterDef(id="mask_dude", name="Mask Dude", asset_dir=os.path.join(_CHARACTERS_DIR, "MaskDude")))
_register(CharacterDef(id="pink_man", name="Pink Man", asset_dir=os.path.join(_CHARACTERS_DIR, "PinkMan")))
_register(CharacterDef(id="virtual_guy", name="Virtual Guy", asset_dir=os.path.join(_CHARACTERS_DIR, "VirtualGuy")))

DEFAULT_CHARACTER_ID = "ninja_frog"


def get(character_id: str) -> CharacterDef:
    return _CHARACTERS[character_id]


def all_characters() -> List[CharacterDef]:
    return list(_CHARACTERS.values())
