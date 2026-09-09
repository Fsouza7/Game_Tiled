"""Headless tests for Phase 10: the Slime King boss -- registry/spawner
safety (never randomly spawned), the summon idol item/recipe/consumption,
phase transitions and their distinct attacks (ranged lob, enrage minions,
landing stomp), and the exclusive drop/coin bounty on defeat.
"""
import random

import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    BOSS_PHASE_2_HEALTH_RATIO, BOSS_PHASE_3_HEALTH_RATIO, SLIME_KING_MINION_COUNT,
    BOSS_COIN_BOUNTY,
)
from game.entities import enemy_registry, boss_ai
from game.entities.boss import Boss
from game.entities.enemy import Enemy
from game.entities.enemy_def import AIType
from game.entities.enemy_spawner import EnemySpawner
from game.entities.player import Player
from game.combat import combat_system
from game.combat.enemy_projectile import EnemyProjectile
from game.crafting import recipe_registry
from game.items import item_registry
from game.world.world import World


def _make_player_at(world, x_tile):
    surface_y = world.surface_spawn_y(x_tile) + 1
    return Player(x_tile * TILE_SIZE, (surface_y - 1) * TILE_SIZE)


# --- registry / spawner safety ---

def test_slime_king_is_registered_as_a_boss_with_a_guaranteed_drop():
    boss_def = enemy_registry.get("slime_king")
    assert boss_def.ai_type == AIType.BOSS
    assert boss_def.spawn_weight == 0.0
    assert boss_def.drop_item_id == "slime_king_core"
    assert boss_def.drop_chance == 1.0
    item_registry.get(boss_def.drop_item_id)  # raises if missing


def test_spawner_never_produces_a_boss():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    spawner = EnemySpawner()
    enemies = []
    for _ in range(500):
        spawner.time_until_next_spawn = 0.0
        spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
        enemies = [e for e in enemies if e.alive]
    assert all(e.enemy_def.ai_type != AIType.BOSS for e in enemies)


# --- items / recipes ---

def test_boss_idol_and_crown_items_are_registered():
    idol = item_registry.get("slime_core_idol")
    assert idol.summons_boss_id == "slime_king"
    core = item_registry.get("slime_king_core")
    assert core.category.value == "material"
    crown = item_registry.get("slime_king_crown")
    assert crown.equip_slot == "head"
    assert crown.defense > item_registry.get("arcane_helmet").defense


def test_boss_recipes_are_registered():
    idol_recipe = recipe_registry.get("slime_core_idol")
    assert idol_recipe.result_item_id == "slime_core_idol"
    crown_recipe = recipe_registry.get("slime_king_crown")
    assert crown_recipe.result_item_id == "slime_king_crown"
    assert ("slime_king_core", 1) in crown_recipe.ingredients


# --- summon idol usage ---

def test_use_selected_summon_item_consumes_idol_and_returns_boss_id():
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    player.inventory.add_item("slime_core_idol", 1)
    player.inventory.select_hotbar(1)  # slot 0 is the starter pickaxe
    boss_id = player.use_selected_summon_item()
    assert boss_id == "slime_king"
    assert player.inventory.count_item("slime_core_idol") == 0


def test_use_selected_summon_item_is_a_noop_for_non_idol_items():
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)  # slot 0 is the starter pickaxe
    assert player.use_selected_summon_item() is None
    assert player.inventory.count_item("wood_sword") == 1


# --- GameApp wiring ---

def test_try_summon_boss_spawns_and_blocks_a_second_summon():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.player.inventory.add_item("slime_core_idol", 2)
        app.player.inventory.select_hotbar(1)  # slot 0 is the starter pickaxe

        app.try_summon_boss()
        bosses = [e for e in app.enemies if isinstance(e, Boss)]
        assert len(bosses) == 1
        assert app.player.inventory.count_item("slime_core_idol") == 1

        app.try_summon_boss()  # a boss is already active -- should no-op, not consume a second idol
        bosses = [e for e in app.enemies if isinstance(e, Boss)]
        assert len(bosses) == 1
        assert app.player.inventory.count_item("slime_core_idol") == 1
    finally:
        pygame.quit()


def test_try_summon_boss_does_nothing_without_an_idol_selected():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.try_summon_boss()
        assert not any(isinstance(e, Boss) for e in app.enemies)
    finally:
        pygame.quit()


# --- boss AI: phases, ranged attack, enrage minions, stomp ---

def _make_boss(world, x_tile):
    surface_y = world.surface_spawn_y(x_tile) + 1
    boss_def = enemy_registry.get("slime_king")
    return Boss(boss_def, x_tile * TILE_SIZE, (surface_y - 1) * TILE_SIZE)


def test_boss_phase1_has_no_ranged_attack():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    boss = _make_boss(world, x)
    player = _make_player_at(world, x + 30)

    fired = False
    for _ in range(300):
        projectile, minions = boss_ai.update(boss, world, player, dt=1 / 60)
        if projectile is not None:
            fired = True
        assert minions == []
    assert boss.phase_index == 0
    assert fired is False


def test_boss_enters_phase2_and_fires_a_lob():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    boss = _make_boss(world, x)
    player = _make_player_at(world, x + 5)
    boss.health = boss.enemy_def.max_health * (BOSS_PHASE_2_HEALTH_RATIO - 0.01)

    fired = None
    for _ in range(300):
        projectile, _ = boss_ai.update(boss, world, player, dt=1 / 60)
        if projectile is not None:
            fired = projectile
            break
    assert boss.phase_index == 1
    assert isinstance(fired, EnemyProjectile)
    assert fired.damage > 0


def test_boss_enters_phase3_once_spawns_minions_and_sets_stomp_on_landing():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    boss = _make_boss(world, x)
    player = _make_player_at(world, x + 30)  # far away -- don't get hit by the lob
    boss.health = boss.enemy_def.max_health * (BOSS_PHASE_3_HEALTH_RATIO - 0.01)

    all_minions = []
    stomped = False
    for _ in range(400):
        _, minions = boss_ai.update(boss, world, player, dt=1 / 60)
        all_minions.extend(minions)
        if boss.stomp_pending:
            stomped = True

    assert boss.phase_index == 2
    assert boss.enraged is True
    assert len(all_minions) == SLIME_KING_MINION_COUNT
    assert all(isinstance(m, Enemy) and not isinstance(m, Boss) for m in all_minions)
    assert stomped is True

    # Health doesn't recover in this game, so phase_index/enraged must be
    # stable -- calling update again must never spawn a second batch.
    _, more_minions = boss_ai.update(boss, world, player, dt=1 / 60)
    assert more_minions == []


# --- combat resolution: enemy projectiles and the stomp shockwave ---

def test_enemy_projectile_damages_player_and_respects_defense():
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    # Settle onto the ground first -- the raw spawn position from
    # _make_player_at overlaps the surface tile at its exact center (only
    # gravity/collision resolves that), and a projectile spawned there
    # would otherwise be discarded by the solid-tile check before ever
    # reaching the player-collision check below.
    for _ in range(10):
        player.physics_step(world, 1 / 60)
    projectile = EnemyProjectile(player.center_x, player.center_y, 0.0, 0.0, damage=20.0)

    starting_hp = player.health
    survivors = combat_system.update_enemy_projectiles(player, [projectile], world, dt=1 / 60)
    assert survivors == []
    expected_damage = max(1.0, 20.0 - combat_system.player_total_defense(player))
    assert player.health == starting_hp - expected_damage
    assert player.is_invulnerable() is True


def test_enemy_projectile_expires_and_is_blocked_by_solid_tiles():
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)

    expiring = EnemyProjectile(TILE_SIZE * 10, TILE_SIZE * 10, 0.0, 0.0, damage=1.0)
    expiring.time_remaining = 0.001
    assert combat_system.update_enemy_projectiles(player, [expiring], world, dt=1 / 60) == []

    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    blocked = EnemyProjectile(x * TILE_SIZE, surface_y * TILE_SIZE, 0.0, 0.0, damage=1.0)
    assert combat_system.update_enemy_projectiles(player, [blocked], world, dt=1 / 60) == []


def test_resolve_boss_stomp_hits_within_radius_and_always_clears_the_flag():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    boss = _make_boss(world, x)
    player = _make_player_at(world, x + 1)  # within stomp radius
    boss.stomp_pending = True

    starting_hp = player.health
    combat_system.resolve_boss_stomp(player, [boss])
    assert player.health < starting_hp
    assert boss.stomp_pending is False  # consumed, whether or not it hit

    # Far away: the flag is still cleared, but no damage happens.
    boss.stomp_pending = True
    far_player = _make_player_at(world, x + 30)
    hp_before = far_player.health
    combat_system.resolve_boss_stomp(far_player, [boss])
    assert far_player.health == hp_before
    assert boss.stomp_pending is False


# --- melee/ranged compatibility (Boss is just an Enemy subclass) ---

def test_boss_can_be_melee_damaged_like_any_enemy():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    player = _make_player_at(world, x)
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)

    boss = _make_boss(world, x + 1)
    player.attack_cooldown_remaining = 0.0
    combat_system.try_attack(player, world, [boss], (boss.center_x, boss.center_y))
    assert boss.health < boss.enemy_def.max_health


# --- defeat rewards ---

def test_boss_defeat_grants_exclusive_drop_and_coin_bounty():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False

        boss = _make_boss(app.world, WORLD_WIDTH_TILES // 2)
        boss.health = 0.0
        boss.alive = False
        boss.defeated = True
        app.enemies.append(boss)

        starting_coins = app.player.inventory.count_item("coin")
        app._collect_enemy_drops()
        assert app.player.inventory.count_item("slime_king_core") == 1
        assert app.player.inventory.count_item("coin") == starting_coins + BOSS_COIN_BOUNTY
        assert boss.drop_collected is True
    finally:
        pygame.quit()
