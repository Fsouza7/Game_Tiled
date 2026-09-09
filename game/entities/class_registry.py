"""Central, data-driven table of every playable character class.

Same shape as character_registry.py (that one picks a *skin*, this one
picks a *playstyle*). A class gates which ItemDef.weapon_class values
try_attack will honor (see game/combat/combat_system.py) -- Warrior is the
default and reproduces exactly today's behavior since every existing
weapon defaults to weapon_class="normal".
"""
from typing import Dict, List

from game.entities.class_def import ClassDef

_CLASSES: Dict[str, ClassDef] = {}


def _register(class_def: ClassDef) -> None:
    if class_def.id in _CLASSES:
        raise ValueError(f"Duplicate class id {class_def.id}")
    _CLASSES[class_def.id] = class_def


_register(ClassDef(
    id="warrior", name="Warrior",
    description="Fights with any sword or bow. The classic playstyle.",
    allowed_weapon_classes=("normal",),
))

_register(ClassDef(
    id="summoner", name="Summoner",
    description="Fights through a summoned minion instead of swinging a "
                 "weapon directly. Starts with a Twig Rod; craft a better "
                 "rod to summon something stronger.",
    allowed_weapon_classes=("summon",),
    starting_item_id="summon_rod_wood",
))

DEFAULT_CLASS_ID = "warrior"


def get(class_id: str) -> ClassDef:
    return _CLASSES[class_id]


def all_classes() -> List[ClassDef]:
    return list(_CLASSES.values())
