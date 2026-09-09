"""Character class schema (first class: Summoner -- see class_registry.py)."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ClassDef:
    id: str
    name: str
    description: str
    allowed_weapon_classes: Tuple[str, ...]  # ItemDef.weapon_class values this class can attack with
    starting_item_id: Optional[str] = None   # granted once, on confirming this class
