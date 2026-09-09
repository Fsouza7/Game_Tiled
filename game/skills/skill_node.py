"""Skill-point tree node schema -- see skill_tree_registry.py."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SkillNodeDef:
    id: str
    skill_id: str
    name: str
    description: str
    required_level: int
    requires_node_id: Optional[str] = None  # prior tier's node id -- None for a tier-1 node
