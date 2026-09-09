"""Central, data-driven table of every skill-point tree node. Each skill
(see skills.py's SKILL_IDS) gets a small 3-tier tree of passive upgrades,
each tier gated behind both a level requirement AND the previous tier
being unlocked (SkillNodeDef.requires_node_id) -- a real chain, not just
a level gate, so it reads as a tree you climb rather than a flat list.
Points are earned from leveling that skill -- see Skills.try_unlock_node.

Effects themselves aren't generic (no "effect engine"): each node id is
checked explicitly at its one call site (in Skills' multiplier/bonus
helpers, or directly in combat_system.py/crafting_system.py), the same
explicit-field style already used throughout this codebase (e.g.
TileDef.bounce_velocity/speed_multiplier).
"""
from typing import Dict, List

from game.skills.skill_node import SkillNodeDef

_NODES: Dict[str, SkillNodeDef] = {}


def _register(node: SkillNodeDef) -> None:
    if node.id in _NODES:
        raise ValueError(f"Duplicate skill node id {node.id}")
    _NODES[node.id] = node


_register(SkillNodeDef(
    id="attack_keen_edge", skill_id="attack", name="Keen Edge",
    description="+10% melee/ranged weapon damage.",
    required_level=10,
))
_register(SkillNodeDef(
    id="attack_berserker", skill_id="attack", name="Berserker",
    description="+15% melee/ranged weapon damage (stacks with Keen Edge).",
    required_level=30, requires_node_id="attack_keen_edge",
))
_register(SkillNodeDef(
    id="attack_deadly_precision", skill_id="attack", name="Deadly Precision",
    description="+20% melee/ranged weapon damage (stacks with the others).",
    required_level=50, requires_node_id="attack_berserker",
))

_register(SkillNodeDef(
    id="defense_thick_skin", skill_id="defense", name="Thick Skin",
    description="+5 flat defense.",
    required_level=10,
))
_register(SkillNodeDef(
    id="defense_unbreakable", skill_id="defense", name="Unbreakable",
    description="+10 flat defense (stacks with Thick Skin).",
    required_level=30, requires_node_id="defense_thick_skin",
))
_register(SkillNodeDef(
    id="defense_fortress", skill_id="defense", name="Fortress",
    description="+15 flat defense (stacks with the others).",
    required_level=50, requires_node_id="defense_unbreakable",
))

_register(SkillNodeDef(
    id="magic_empowered_bond", skill_id="magic", name="Empowered Bond",
    description="+15% summon damage.",
    required_level=10,
))
_register(SkillNodeDef(
    id="magic_swift_familiar", skill_id="magic", name="Swift Familiar",
    description="Summon moves 20% faster and attacks 15% more often.",
    required_level=30, requires_node_id="magic_empowered_bond",
))
_register(SkillNodeDef(
    id="magic_arcane_mastery", skill_id="magic", name="Arcane Mastery",
    description="+25% summon damage (stacks with Empowered Bond).",
    required_level=50, requires_node_id="magic_swift_familiar",
))

_register(SkillNodeDef(
    id="mining_efficient_strikes", skill_id="mining", name="Efficient Strikes",
    description="+20% mining power.",
    required_level=10,
))
_register(SkillNodeDef(
    id="mining_deep_delver", skill_id="mining", name="Deep Delver",
    description="Mines 20% faster.",
    required_level=30, requires_node_id="mining_efficient_strikes",
))
_register(SkillNodeDef(
    id="mining_master_prospector", skill_id="mining", name="Master Prospector",
    description="+30% mining power (stacks with Efficient Strikes).",
    required_level=50, requires_node_id="mining_deep_delver",
))

_register(SkillNodeDef(
    id="crafting_resourceful", skill_id="crafting", name="Resourceful",
    description="15% chance to refund one ingredient stack when crafting.",
    required_level=10,
))
_register(SkillNodeDef(
    id="crafting_master", skill_id="crafting", name="Crafting Master",
    description="+50% Crafting XP gained.",
    required_level=30, requires_node_id="crafting_resourceful",
))
_register(SkillNodeDef(
    id="crafting_artisan", skill_id="crafting", name="Artisan",
    description="+25% Crafting XP gained (stacks with Crafting Master).",
    required_level=50, requires_node_id="crafting_master",
))


def get(node_id: str) -> SkillNodeDef:
    return _NODES[node_id]


def all_nodes() -> List[SkillNodeDef]:
    return list(_NODES.values())


def nodes_for_skill(skill_id: str) -> List[SkillNodeDef]:
    return [node for node in _NODES.values() if node.skill_id == skill_id]
