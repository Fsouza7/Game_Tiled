"""Headless tests for the Summoner rod tooltip fix (user feedback: "os
status do summoner nas rods nao aparece, quantidades de summon, dano do
summon já com base no magic level"). Before this fix, a summon rod's
ItemDef.damage/is_ranged always default to 0.0/False (the real numbers
live on the SummonDef it casts), so every rod's tooltip showed a
meaningless "Damage: 0" / "Melee" pair instead of anything about the
summon it actually casts -- see Renderer._summon_rod_stat_lines.
"""
import dataclasses

import pygame  # noqa: F401

from game.entities.player import Player
from game.entities import summon_registry
from game.items import item_registry
from game.rendering.renderer import Renderer


def _make_player():
    return Player(0, 0)


def _bare_renderer() -> Renderer:
    # Skips Renderer.__init__ (which loads fonts/textures and needs a real
    # display surface) -- the functions under test here are pure and only
    # touch registries, same pattern as test_equipment.py's
    # test_item_tooltip_stat_lines_vary_by_category.
    return Renderer.__new__(Renderer)


def test_summon_rod_stat_lines_shows_the_cast_summon_and_its_base_damage():
    renderer = _bare_renderer()
    rod_def = item_registry.get("summon_rod_iron")
    summon_def = summon_registry.get(rod_def.summons_id)

    lines = renderer._summon_rod_stat_lines(rod_def, player=None)
    text = [t for t, _ in lines]

    assert any(summon_def.name in t for t in text)
    assert any(f"{summon_def.damage:.0f}" in t and "Summon Damage" in t for t in text)


def test_summon_rod_stat_lines_shows_effective_damage_scaled_by_magic_level():
    renderer = _bare_renderer()
    rod_def = item_registry.get("summon_rod_iron")
    summon_def = summon_registry.get(rod_def.summons_id)
    player = _make_player()

    baseline_multiplier = player.skills.magic_damage_multiplier()
    lines_before = renderer._summon_rod_stat_lines(rod_def, player)
    text_before = [t for t, _ in lines_before]
    expected_before = summon_def.damage * baseline_multiplier
    assert any(f"{expected_before:.0f}" in t and "Effective Damage" in t for t in text_before)

    # Leveling Magic should raise the multiplier and the shown effective damage with it.
    player.skills.add_xp("magic", 50000.0)
    boosted_multiplier = player.skills.magic_damage_multiplier()
    assert boosted_multiplier > baseline_multiplier

    lines_after = renderer._summon_rod_stat_lines(rod_def, player)
    text_after = [t for t, _ in lines_after]
    expected_after = summon_def.damage * boosted_multiplier
    assert any(f"{expected_after:.0f}" in t and "Effective Damage" in t for t in text_after)
    assert expected_after > expected_before


def test_summon_rod_stat_lines_without_a_player_omits_effective_damage_but_still_shows_base():
    renderer = _bare_renderer()
    rod_def = item_registry.get("summon_rod_wood")

    lines = renderer._summon_rod_stat_lines(rod_def, player=None)
    text = [t for t, _ in lines]

    assert not any("Effective Damage" in t for t in text)
    assert any("Summon Damage" in t for t in text)
    assert any("Summons:" in t for t in text)


def test_summon_rod_stat_lines_includes_attack_speed_range_and_move_speed():
    renderer = _bare_renderer()
    rod_def = item_registry.get("summon_rod_iron")
    summon_def = summon_registry.get(rod_def.summons_id)

    lines = renderer._summon_rod_stat_lines(rod_def, player=None)
    text = [t for t, _ in lines]

    assert any("Attack Speed" in t and f"{summon_def.attack_interval_s:.1f}" in t for t in text)
    assert any("Attack Range" in t and f"{summon_def.attack_range_tiles:.1f}" in t for t in text)
    assert any("Summon Move Speed" in t and f"{summon_def.move_speed:.1f}" in t for t in text)


def test_summon_rod_stat_lines_shows_crit_chance_when_the_rod_has_one():
    renderer = _bare_renderer()
    rod_def = dataclasses.replace(item_registry.get("summon_rod_arcane"), crit_chance=0.2)

    lines = renderer._summon_rod_stat_lines(rod_def, player=None)
    text = [t for t, _ in lines]

    assert any("Crit Chance: 20%" in t for t in text)


def test_item_tooltip_stat_lines_routes_a_summon_rod_to_the_summon_block_not_the_generic_weapon_block():
    """Regression test for the actual bug: a rod's is_weapon=True used to
    always hit the generic "Damage: X" / "Melee"/"Ranged" branch, which
    for every rod meant "Damage: 0" / "Melee" (is_ranged defaults False)
    -- neither number means anything for a summon rod."""
    renderer = _bare_renderer()
    rod_def = item_registry.get("summon_rod_iron")
    player = _make_player()

    lines = renderer._item_tooltip_stat_lines(rod_def, player)
    text = [t for t, _ in lines]

    assert not any(t == "Damage: 0" for t in text)
    assert not any(t == "Melee" for t in text)
    assert any("Summons:" in t for t in text)
    assert any("Effective Damage" in t for t in text)


def test_item_tooltip_stat_lines_still_shows_plain_damage_for_a_normal_weapon():
    """The fix must not regress ordinary (non-rod) weapons -- they should
    keep using the plain Damage/Melee-or-Ranged lines, not the summon block."""
    renderer = _bare_renderer()
    sword_def = item_registry.get("iron_sword")

    lines = renderer._item_tooltip_stat_lines(sword_def, player=None)
    text = [t for t, _ in lines]

    assert any(t == f"Damage: {sword_def.damage:.0f}" for t in text)
    assert any(t in ("Melee", "Ranged") for t in text)
    assert not any("Summons:" in t for t in text)


def test_every_registered_summon_rod_resolves_a_real_summon_def():
    """Guards _summon_rod_stat_lines against a future rod whose summons_id
    doesn't resolve (would raise inside the tooltip draw call)."""
    renderer = _bare_renderer()
    for item_id, item_def in item_registry.all_items().items():
        if item_def.weapon_class != "summon":
            continue
        lines = renderer._summon_rod_stat_lines(item_def, player=None)
        assert lines, f"{item_id} produced no stat lines"
