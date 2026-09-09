"""Headless tests for the RPG skill/leveling system: the RuneScape XP
curve, Skills.add_xp/level-up queuing, the skill-point tree, and every
combat/mining/crafting hook point that grants XP or applies a skill bonus.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CRAFTING_XP_PER_CRAFT,
    MINING_XP_PER_BREAK,
)
from game.entities.player import Player
from game.entities.enemy import Enemy
from game.entities.summon import Summon
from game.entities import enemy_registry, summon_registry, summon_ai
from game.combat import combat_system
from game.crafting import recipe_registry, crafting_system
from game.skills import xp_table, skill_tree_registry
from game.skills.skills import Skills, SKILL_IDS
from game.world.world import World
from game.world.tile_registry import STONE_ID


def _make_world_and_player(x_offset: int = 0):
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2 + x_offset
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player, x, surface_y


# --- XP table ---

def test_xp_table_matches_known_runescape_reference_values():
    assert xp_table.LEVEL_XP_TABLE[1] == 0
    assert xp_table.LEVEL_XP_TABLE[2] == 83
    assert xp_table.LEVEL_XP_TABLE[10] == 1154
    assert xp_table.LEVEL_XP_TABLE[99] == 13034431


def test_xp_table_is_monotonically_non_decreasing():
    values = xp_table.LEVEL_XP_TABLE[1:]
    assert all(b >= a for a, b in zip(values, values[1:]))


def test_level_for_xp_clamps_and_finds_thresholds():
    assert xp_table.level_for_xp(0) == 1
    assert xp_table.level_for_xp(-5) == 1
    assert xp_table.level_for_xp(82) == 1
    assert xp_table.level_for_xp(83) == 2
    assert xp_table.level_for_xp(xp_table.MAX_XP) == 99
    assert xp_table.level_for_xp(xp_table.MAX_XP + 1_000_000) == 99  # no error past the cap


# --- Skills.add_xp / level-up queue ---

def test_add_xp_below_next_level_queues_nothing():
    skills = Skills()
    skills.add_xp("attack", 10.0)
    assert skills.level("attack") == 1
    assert skills.drain_level_ups() == []


def test_add_xp_crossing_one_level_queues_it():
    skills = Skills()
    skills.add_xp("attack", 83.0)  # exactly the level-2 threshold
    assert skills.level("attack") == 2
    assert skills.drain_level_ups() == [("attack", 2)]


def test_add_xp_crossing_multiple_levels_queues_all_of_them():
    skills = Skills()
    skills.add_xp("mining", 1154.0)  # level 10 in one grant
    levels = skills.drain_level_ups()
    assert levels == [("mining", lvl) for lvl in range(2, 11)]


def test_drain_level_ups_clears_the_queue():
    skills = Skills()
    skills.add_xp("magic", 83.0)
    skills.drain_level_ups()
    assert skills.drain_level_ups() == []


def test_add_xp_is_a_noop_for_zero_or_negative():
    skills = Skills()
    skills.add_xp("crafting", 0.0)
    skills.add_xp("crafting", -5.0)
    assert skills.xp("crafting") == 0.0


# --- skill-tree registry sanity ---

def test_skill_tree_registry_has_three_nodes_per_combat_and_gathering_skill():
    combat_and_gathering_skills = ("attack", "defense", "magic", "mining", "crafting")
    for skill_id in combat_and_gathering_skills:
        nodes = skill_tree_registry.nodes_for_skill(skill_id)
        assert len(nodes) == 3
        levels = [n.required_level for n in nodes]
        assert levels == sorted(levels)  # ascending, tier 1 before tier 2 before tier 3
        # A real chain: tier 1 has no prerequisite, tiers 2/3 require the
        # previous tier's node specifically (not just a level gate).
        assert nodes[0].requires_node_id is None
        assert nodes[1].requires_node_id == nodes[0].id
        assert nodes[2].requires_node_id == nodes[1].id

    assert skill_tree_registry.nodes_for_skill("hitpoints") == []


def test_skill_tree_node_ids_are_unique_and_reference_valid_skills():
    seen = set()
    for node in skill_tree_registry.all_nodes():
        assert node.id not in seen
        seen.add(node.id)
        assert node.skill_id in SKILL_IDS


# --- skill-point tree unlocking ---

def test_try_unlock_node_fails_below_required_level():
    skills = Skills()
    assert skills.try_unlock_node("attack_keen_edge") is False
    assert skills.has_node("attack_keen_edge") is False


def test_try_unlock_node_fails_with_zero_available_points():
    skills = Skills()
    skills.add_xp("attack", xp_table.LEVEL_XP_TABLE[10])  # level 10 -> 9 points
    assert skills.available_points("attack") == 9
    # available_points is derived from len(unlocked_node_ids), so stuffing
    # it with placeholder entries simulates "already spent all points
    # elsewhere" without needing 9 real registered nodes to exist.
    skills.restore_state("attack", skills.xp("attack"), {f"placeholder_{i}" for i in range(9)})
    assert skills.available_points("attack") == 0
    assert skills.try_unlock_node("attack_keen_edge") is False


def test_try_unlock_node_succeeds_and_consumes_a_point():
    skills = Skills()
    skills.add_xp("defense", xp_table.LEVEL_XP_TABLE[10])
    before = skills.available_points("defense")
    assert skills.try_unlock_node("defense_thick_skin") is True
    assert skills.has_node("defense_thick_skin") is True
    assert skills.available_points("defense") == before - 1


def test_try_unlock_node_is_idempotent():
    skills = Skills()
    skills.add_xp("mining", xp_table.LEVEL_XP_TABLE[10])
    assert skills.try_unlock_node("mining_efficient_strikes") is True
    assert skills.try_unlock_node("mining_efficient_strikes") is False  # already unlocked


def test_try_unlock_node_fails_without_the_prior_tier_unlocked():
    skills = Skills()
    skills.add_xp("attack", xp_table.LEVEL_XP_TABLE[50])  # level + points to spare for all 3 tiers
    # attack_berserker (tier 2) requires attack_keen_edge (tier 1) first,
    # even though the level requirement alone is already satisfied.
    assert skills.try_unlock_node("attack_berserker") is False
    assert skills.try_unlock_node("attack_deadly_precision") is False  # tier 3 needs tier 2

    assert skills.try_unlock_node("attack_keen_edge") is True
    assert skills.try_unlock_node("attack_berserker") is True
    assert skills.try_unlock_node("attack_deadly_precision") is True


# --- multiplier/bonus helpers ---

def test_attack_damage_multiplier_baseline_and_with_nodes():
    skills = Skills()
    baseline = skills.attack_damage_multiplier()
    assert baseline > 1.0  # level-1 passive is still a nonzero base multiplier

    skills.add_xp("attack", xp_table.LEVEL_XP_TABLE[30])
    skills.try_unlock_node("attack_keen_edge")
    with_one_node = skills.attack_damage_multiplier()
    assert with_one_node > baseline

    skills.try_unlock_node("attack_berserker")
    with_both_nodes = skills.attack_damage_multiplier()
    assert with_both_nodes > with_one_node


def test_defense_flat_bonus_baseline_and_with_nodes():
    from game.settings import DEFENSE_FLAT_PER_LEVEL

    skills = Skills()
    assert skills.defense_flat_bonus() == DEFENSE_FLAT_PER_LEVEL  # level 1 * per-level bonus, no nodes yet
    skills.add_xp("defense", xp_table.LEVEL_XP_TABLE[30])
    boosted_no_nodes = skills.defense_flat_bonus()
    assert boosted_no_nodes > 0.0

    skills.try_unlock_node("defense_thick_skin")
    with_thick_skin = skills.defense_flat_bonus()
    assert with_thick_skin == boosted_no_nodes + 5.0

    skills.try_unlock_node("defense_unbreakable")
    assert skills.defense_flat_bonus() == with_thick_skin + 10.0


def test_mining_power_multiplier_and_crafting_xp_multiplier():
    skills = Skills()
    assert skills.mining_power_multiplier() >= 1.0
    assert skills.crafting_xp_multiplier() == 1.0

    skills.add_xp("crafting", xp_table.LEVEL_XP_TABLE[30])
    skills.try_unlock_node("crafting_resourceful")  # tier-1 prerequisite for crafting_master
    skills.try_unlock_node("crafting_master")
    assert skills.crafting_xp_multiplier() == 1.5


def test_combat_level_averages_attack_defense_magic_hitpoints():
    skills = Skills()
    assert skills.combat_level() == 1
    skills.add_xp("attack", xp_table.LEVEL_XP_TABLE[10])  # attack=10, rest=1
    assert skills.combat_level() == round((10 + 1 + 1 + 1) / 4)


def test_level_progress_ratio_moves_from_zero_to_near_one_within_a_level():
    skills = Skills()
    assert skills.level_progress_ratio("attack") == 0.0  # exactly at level 1's threshold

    span = xp_table.LEVEL_XP_TABLE[2] - xp_table.LEVEL_XP_TABLE[1]
    skills.add_xp("attack", span - 1)  # just short of leveling up
    assert skills.level("attack") == 1
    assert 0.9 < skills.level_progress_ratio("attack") < 1.0


def test_level_progress_ratio_is_1_at_the_level_cap():
    skills = Skills()
    skills.add_xp("attack", xp_table.MAX_XP)
    assert skills.level("attack") == xp_table.SKILL_MAX_LEVEL
    assert skills.level_progress_ratio("attack") == 1.0


def test_combat_level_progress_ratio_averages_its_four_skills():
    skills = Skills()
    assert skills.combat_level_progress_ratio() == 0.0
    skills.add_xp("attack", xp_table.MAX_XP)  # attack maxed -> its ratio is 1.0
    ratio = skills.combat_level_progress_ratio()
    assert 0.0 < ratio < 1.0  # attack contributes 1.0, the other 3 still contribute 0.0


def test_player_total_defense_combines_equipment_and_skill_bonus():
    _, player, _, _ = _make_world_and_player()
    assert combat_system.player_total_defense(player) == player.skills.defense_flat_bonus()

    player.inventory.add_item("wood_helmet", 1)
    player.equipment.equip_from_inventory(player.inventory, "wood_helmet")
    equipment_defense = player.equipment.total_defense()
    assert equipment_defense > 0
    assert combat_system.player_total_defense(player) == equipment_defense + player.skills.defense_flat_bonus()


# --- Attack XP (melee + ranged) ---

def test_melee_hit_grants_attack_and_hitpoints_xp():
    world, player, x, surface_y = _make_world_and_player()
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)

    combat_system.try_attack(player, world, [enemy], (player.center_x + 1, player.center_y))

    assert player.skills.xp("attack") > 0.0
    assert player.skills.xp("hitpoints") > 0.0  # a fraction of combat xp also trains hitpoints


def test_melee_kill_grants_bonus_attack_xp():
    world, player, x, surface_y = _make_world_and_player()
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)
    weak_enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)
    weak_enemy.health = 0.01  # one hit away from defeated

    combat_system.try_attack(player, world, [weak_enemy], (player.center_x + 1, player.center_y))

    assert weak_enemy.defeated is True
    xp_with_kill_bonus = player.skills.xp("attack")

    # Compare against a fresh player landing the same hit on a full-health
    # (not-about-to-die) enemy -- no kill bonus should apply there.
    world2, player2, _, _ = _make_world_and_player(x_offset=10)
    player2.inventory.add_item("wood_sword", 1)
    player2.inventory.select_hotbar(1)
    healthy_enemy = Enemy(enemy_registry.get("slime"), player2.center_x + TILE_SIZE * 0.5, player2.center_y)
    combat_system.try_attack(player2, world2, [healthy_enemy], (player2.center_x + 1, player2.center_y))

    assert xp_with_kill_bonus > player2.skills.xp("attack")


def test_attack_level_multiplier_increases_actual_melee_damage():
    world, player, x, surface_y = _make_world_and_player()
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)
    player.skills.add_xp("attack", xp_table.LEVEL_XP_TABLE[30])
    player.skills.try_unlock_node("attack_keen_edge")
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)
    start_health = enemy.health

    combat_system.try_attack(player, world, [enemy], (player.center_x + 1, player.center_y))

    from game.items import item_registry
    base_damage = item_registry.get("wood_sword").damage
    actual_damage = start_health - enemy.health
    assert actual_damage > base_damage


def test_ranged_hit_grants_attack_xp():
    # High in open air (well above the surface) so the projectile's flight
    # path isn't blocked by solid ground right under the player's feet --
    # same precedent as the Summoner tests' flying-summon-in-air setup.
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    air_y = (world.surface_spawn_y(x) - 6) * TILE_SIZE
    player = Player(x * TILE_SIZE, air_y)
    player.inventory.add_item("wood_bow", 1)
    player.inventory.add_item("arrow", 5)
    player.inventory.select_hotbar(1)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE, air_y)

    # Aim exactly at the enemy's own center (not just "far to the right")
    # so the shot's trajectory is guaranteed to line up with its rect
    # regardless of the two entities' differing heights.
    projectile = combat_system.try_attack(player, world, [enemy], (enemy.center_x, enemy.center_y))
    assert projectile is not None
    projectiles = [projectile]
    for _ in range(60):  # give the projectile (PROJECTILE_SPEED px/frame) time to reach the enemy
        projectiles = combat_system.update_projectiles(player, projectiles, world, [enemy], dt=1 / 60)
        if not projectiles:
            break

    assert player.skills.xp("attack") > 0.0


# --- Magic XP (summon) ---

def test_summon_hit_grants_magic_and_hitpoints_xp():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    air_y = (world.surface_spawn_y(x) - 6) * TILE_SIZE
    player = Player(x * TILE_SIZE, air_y, class_id="summoner")
    summon = Summon(summon_registry.get("twig_sprite"), player.center_x, player.center_y)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)

    for _ in range(120):
        summon_ai.update(summon, world, player, [enemy], dt=1 / 60)
        combat_system.resolve_summon_attacks(player, [summon], [enemy])

    assert player.skills.xp("magic") > 0.0
    assert player.skills.xp("hitpoints") > 0.0


def test_magic_level_multiplier_boosts_summon_damage_at_cast_time():
    from game.combat.combat_system import _try_summon_cast
    from game.items import item_registry

    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = Player(x * TILE_SIZE, world.surface_spawn_y(x) * TILE_SIZE, class_id="summoner")
    item_def = item_registry.get("summon_rod_wood")
    base_damage = summon_registry.get(item_def.summons_id).damage

    summon = _try_summon_cast(player, item_def)
    assert summon.damage >= base_damage  # level 1, no nodes -> baseline-ish multiplier

    player.skills.add_xp("magic", xp_table.LEVEL_XP_TABLE[30])
    player.skills.try_unlock_node("magic_empowered_bond")
    boosted_summon = _try_summon_cast(player, item_def)
    assert boosted_summon.damage > summon.damage


# --- Defense XP ---

def test_taking_contact_damage_grants_defense_and_hitpoints_xp():
    world, player, x, surface_y = _make_world_and_player()
    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)

    combat_system.resolve_contact_damage(player, [enemy])

    assert player.skills.xp("defense") > 0.0
    assert player.skills.xp("hitpoints") > 0.0


def test_defense_skill_bonus_measurably_reduces_damage_taken():
    world, player, x, surface_y = _make_world_and_player()
    player.skills.add_xp("defense", xp_table.LEVEL_XP_TABLE[30])
    player.skills.try_unlock_node("defense_thick_skin")
    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)

    world2, player2, x2, surface_y2 = _make_world_and_player(x_offset=10)
    enemy2 = Enemy(enemy_registry.get("crawler"), x2 * TILE_SIZE, (surface_y2 - 1) * TILE_SIZE)

    start1, start2 = player.health, player2.health
    combat_system.resolve_contact_damage(player, [enemy])
    combat_system.resolve_contact_damage(player2, [enemy2])

    damage_with_defense_skill = start1 - player.health
    damage_without = start2 - player2.health
    assert damage_with_defense_skill < damage_without


# --- Mining XP ---

def test_breaking_a_tile_grants_mining_xp():
    world, player, x, surface_y = _make_world_and_player()
    tile_x, tile_y = x, surface_y  # a stone/dirt column beneath the grass surface
    player.inventory.slots[0].item_id = "wood_pickaxe"

    drop = None
    for _ in range(200):
        drop = player.try_mine(world, tile_x, tile_y + 1, dt=1.0)
        if drop is not None:
            break
    assert drop is not None
    assert player.skills.xp("mining") == MINING_XP_PER_BREAK


def test_mining_level_multiplier_increases_effective_power():
    world, player, x, surface_y = _make_world_and_player()
    player.inventory.slots[0].item_id = "wood_pickaxe"
    tile_id = world.get_tile(x, surface_y + 1)

    base_power = player.mining_power_against(tile_id)
    player.skills.add_xp("mining", xp_table.LEVEL_XP_TABLE[30])
    player.skills.try_unlock_node("mining_efficient_strikes")
    boosted_power = player.mining_power_against(tile_id)

    assert boosted_power > base_power


# --- Crafting XP ---

def test_successful_craft_grants_crafting_xp():
    world, player, x, surface_y = _make_world_and_player()
    player.inventory.add_item("wood", 20)
    recipe = recipe_registry.get("wood_pickaxe")

    success, _ = crafting_system.craft_and_discover(recipe, player, world)

    assert success is True
    assert player.skills.xp("crafting") == CRAFTING_XP_PER_CRAFT


def test_crafting_resourceful_node_can_refund_an_ingredient():
    world, player, x, surface_y = _make_world_and_player()
    player.skills.add_xp("crafting", xp_table.LEVEL_XP_TABLE[30])
    player.skills.try_unlock_node("crafting_resourceful")
    # A stackable result (unlike a max_stack=1 tool) so 50 crafts don't
    # fill up the inventory with distinct single-item stacks.
    recipe = recipe_registry.get("wood_plank_block")  # (("wood", 1),) -> 4 planks

    import random
    random.seed(1)  # deterministic: this seed refunds within the loop below
    refunded_at_least_once = False
    for _ in range(50):
        # Reset to a known baseline each attempt (1 wood) rather than
        # letting leftover refunded wood accumulate across iterations.
        current_wood = player.inventory.count_item("wood")
        if current_wood > 0:
            player.inventory.remove_item("wood", current_wood)
        player.inventory.add_item("wood", 1)

        success, _ = crafting_system.craft_and_discover(recipe, player, world)
        assert success is True
        # A normal craft consumes the 1 wood, leaving 0 -- a refund leaves 1.
        if player.inventory.count_item("wood") > 0:
            refunded_at_least_once = True
            break
    assert refunded_at_least_once


# --- full GameApp: level-up announcement + Skills screen interaction ---

def test_game_app_announces_level_ups_and_skills_screen_interaction():
    from game.core.game_app import GameApp
    from game.rendering.renderer import skill_row_rect, skill_node_rect

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.character_select_open = False
        app.class_select_open = False

        starting_max_health = app.player.max_health
        app.player.skills.add_xp("hitpoints", xp_table.LEVEL_XP_TABLE[10])  # several level-ups at once
        app.step(dt=1 / 60)  # drains the level-ups and pushes notifications
        app.step(dt=1 / 60)  # NotificationQueue.update() needs a second tick to surface one as current

        assert app.player.max_health > starting_max_health
        assert app.notifications.current_text is not None

        # K opens the Skills screen; clicking a row selects that skill;
        # clicking an eligible node spends a point to unlock it.
        keydown = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k)
        app.input_handler.handle_discrete_events([keydown], app)
        assert app.skills_open is True

        app.player.skills.add_xp("attack", xp_table.LEVEL_XP_TABLE[10])
        attack_index = SKILL_IDS.index("attack")
        row_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=skill_row_rect(attack_index).center)
        app.input_handler.handle_discrete_events([row_click], app)
        assert app.selected_skill_id == "attack"

        node_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=skill_node_rect(0).center)
        app.input_handler.handle_discrete_events([node_click], app)
        assert app.player.skills.has_node("attack_keen_edge") is True

        # A real draw call, same as the other full-app smoke tests, to
        # catch any rendering/layout crash in the new screen.
        app.step(dt=1 / 60)
    finally:
        pygame.quit()
