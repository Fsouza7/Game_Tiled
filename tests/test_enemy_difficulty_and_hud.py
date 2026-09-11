"""Headless tests for two user-requested features (pt-BR: "vamos fazer a
progressao do jogo, cada dia que passa os mobs ficam mais fortes, e
coloque para mostrar a vida deles e o nome em cima do sprite"):

1. Day-based enemy difficulty scaling (game/entities/difficulty.py) --
   freshly-spawned enemies get tougher (health) and hit harder (contact
   damage) the more in-game days have passed, capped so it doesn't scale
   forever.
2. A floating name + HP bar above every non-boss enemy, always shown (not
   just while damaged), see Renderer._draw_entity_health_bar.
"""
import pygame

pygame.init()

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    ENEMY_HEALTH_PCT_PER_DAY, ENEMY_DAMAGE_PCT_PER_DAY, ENEMY_DIFFICULTY_MAX_DAY,
    SLIME_KING_MINION_COUNT,
)
from game.entities import difficulty, enemy_registry, boss_ai
from game.entities.enemy import Enemy
from game.entities.boss import Boss
from game.entities.enemy_def import AIType
from game.entities.enemy_spawner import EnemySpawner
from game.entities.player import Player
from game.rendering.renderer import Renderer, HEALTH_BG, HEALTH_FG
from game.world.world import World


def _make_player_at(world, x_tile):
    surface_y = world.surface_spawn_y(x_tile) + 1
    return Player(x_tile * TILE_SIZE, (surface_y - 1) * TILE_SIZE)


def _bare_renderer() -> Renderer:
    return Renderer.__new__(Renderer)


def _bare_renderer_with_font() -> Renderer:
    # pygame.font.init() is idempotent and cheap -- called fresh here
    # rather than relying on a module-level pygame.init(), since another
    # test module elsewhere in the suite may have already called
    # pygame.quit() (tearing the font subsystem back down) by the time
    # this module's tests run, depending on collection order.
    pygame.font.init()
    renderer = Renderer.__new__(Renderer)
    renderer.font = pygame.font.SysFont("consolas", 14)
    return renderer


# --- difficulty.py: pure multiplier math ---

def test_day_1_is_the_unscaled_baseline():
    assert difficulty.health_multiplier(1) == 1.0
    assert difficulty.damage_multiplier(1) == 1.0


def test_multipliers_grow_by_the_documented_percentage_per_day():
    assert difficulty.health_multiplier(2) == 1.0 + ENEMY_HEALTH_PCT_PER_DAY
    assert difficulty.damage_multiplier(2) == 1.0 + ENEMY_DAMAGE_PCT_PER_DAY
    assert difficulty.health_multiplier(11) == 1.0 + 10 * ENEMY_HEALTH_PCT_PER_DAY


def test_multipliers_are_monotonically_non_decreasing_with_day():
    prev_health, prev_damage = 0.0, 0.0
    for day in range(1, ENEMY_DIFFICULTY_MAX_DAY + 20):
        health = difficulty.health_multiplier(day)
        damage = difficulty.damage_multiplier(day)
        assert health >= prev_health
        assert damage >= prev_damage
        prev_health, prev_damage = health, damage


def test_multipliers_cap_at_the_configured_max_day():
    at_cap = difficulty.health_multiplier(ENEMY_DIFFICULTY_MAX_DAY)
    far_past_cap = difficulty.health_multiplier(ENEMY_DIFFICULTY_MAX_DAY + 500)
    assert at_cap == far_past_cap


def test_a_day_count_below_one_never_produces_a_multiplier_under_baseline():
    # day_count is always >= 1 in practice (WorldClock starts at 1), but
    # this guards the floor doesn't go negative/zero on a bad input.
    assert difficulty.health_multiplier(0) == 1.0
    assert difficulty.damage_multiplier(-5) == 1.0


# --- Enemy/Boss: the multiplier actually lands on the instance ---

def test_enemy_defaults_to_unscaled_stats_matching_enemy_def():
    enemy_def = enemy_registry.get("slime")
    enemy = Enemy(enemy_def, 0, 0)
    assert enemy.max_health == enemy_def.max_health
    assert enemy.health == enemy_def.max_health
    assert enemy.contact_damage == enemy_def.contact_damage


def test_enemy_health_and_damage_multipliers_scale_the_instance_not_the_shared_def():
    enemy_def = enemy_registry.get("slime")
    scaled = Enemy(enemy_def, 0, 0, health_multiplier=2.0, damage_multiplier=1.5)
    assert scaled.max_health == enemy_def.max_health * 2.0
    assert scaled.health == scaled.max_health
    assert scaled.contact_damage == enemy_def.contact_damage * 1.5
    # The frozen, shared EnemyDef itself is never mutated.
    assert enemy_def.max_health == enemy_registry.get("slime").max_health

    unscaled = Enemy(enemy_def, 0, 0)
    assert unscaled.max_health == enemy_def.max_health  # a sibling instance is unaffected


def test_boss_forwards_multipliers_to_its_max_health_and_contact_damage():
    boss_def = enemy_registry.get("slime_king")
    boss = Boss(boss_def, 0, 0, health_multiplier=1.5, damage_multiplier=1.2)
    assert boss.max_health == boss_def.max_health * 1.5
    assert boss.health == boss.max_health
    assert boss.contact_damage == boss_def.contact_damage * 1.2


def test_boss_ai_phase_ratio_uses_the_scaled_max_health():
    """Regression guard: boss_ai used to divide by enemy_def.max_health
    directly, which would have made a scaled boss enter later phases too
    early (its ratio would read lower than it really is)."""
    boss_def = enemy_registry.get("slime_king")
    boss = Boss(boss_def, 0, 0, health_multiplier=2.0)
    boss.health = boss.max_health  # full health, scaled
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    boss_ai.update(boss, world, player, dt=0.016)
    assert boss.phase_index == 0  # still full health -> no premature phase jump


def test_boss_minions_inherit_the_bosss_own_difficulty_scaling():
    boss_def = enemy_registry.get("slime_king")
    boss = Boss(boss_def, 0, 0, health_multiplier=2.0, damage_multiplier=1.4)
    boss.enraged = True  # force the enrage-spawn path in _spawn_minions directly
    minions = boss_ai._spawn_minions(boss)
    assert len(minions) == SLIME_KING_MINION_COUNT
    minion_def = enemy_registry.get(boss_ai.SLIME_MINION_ID)
    for minion in minions:
        assert minion.max_health == minion_def.max_health * 2.0
        assert minion.contact_damage == minion_def.contact_damage * 1.4


# --- EnemySpawner: day_count actually reaches the spawned Enemy ---

def test_spawner_applies_day_based_scaling_to_a_freshly_spawned_enemy():
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    spawner = EnemySpawner()

    baseline = spawner._try_spawn(world, player, is_night=False, underground=False, day_count=1)
    scaled = spawner._try_spawn(world, player, is_night=False, underground=False, day_count=20)

    assert baseline is not None and scaled is not None
    assert baseline.max_health == baseline.enemy_def.max_health  # day 1: unscaled
    if scaled.enemy_def.id == baseline.enemy_def.id:
        assert scaled.max_health > baseline.max_health
        assert scaled.contact_damage >= baseline.contact_damage


def test_spawner_update_defaults_day_count_to_one_when_not_given():
    """Every existing call site/test that calls update() without a
    day_count must keep behaving exactly like before this feature."""
    world = World(DEFAULT_SEED)
    player = _make_player_at(world, WORLD_WIDTH_TILES // 2)
    spawner = EnemySpawner()
    enemies = []
    spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
    spawner.time_until_next_spawn = 0.0
    spawner.update(dt=0.0, world=world, player=player, enemies=enemies, is_night=False)
    if enemies:
        assert enemies[0].max_health == enemies[0].enemy_def.max_health


# --- Renderer: name + HP bar above every non-boss enemy ---

def test_entity_health_bar_draws_name_and_bar_for_a_non_boss_enemy():
    renderer = _bare_renderer_with_font()
    window = pygame.Surface((400, 400), pygame.SRCALPHA)
    enemy = Enemy(enemy_registry.get("slime"), 0, 0)

    renderer._draw_entity_health_bar(window, enemy, screen_x=100, screen_y=200, width=40)

    colors = {window.get_at((x, y))[:3] for x in range(0, 400) for y in range(180, 200)}
    assert HEALTH_FG in colors or HEALTH_BG in colors  # the HP bar itself got drawn somewhere in that band


def test_entity_health_bar_is_always_shown_even_at_full_health():
    """Regression guard: this used to early-return (draw nothing) whenever
    health >= max_health, so a full-health mob had no bar/name at all."""
    renderer = _bare_renderer_with_font()
    window = pygame.Surface((400, 400), pygame.SRCALPHA)
    enemy = Enemy(enemy_registry.get("slime"), 0, 0)
    assert enemy.health == enemy.max_health  # full health

    before = pygame.image.tostring(window, "RGBA")
    renderer._draw_entity_health_bar(window, enemy, screen_x=100, screen_y=200, width=40)
    after = pygame.image.tostring(window, "RGBA")

    assert before != after  # something was actually drawn, not a no-op


def test_entity_health_bar_skips_bosses_entirely():
    """Bosses already get a persistent top-center name+bar (_draw_boss_bar)
    -- drawing a second one floating over the sprite would be redundant."""
    renderer = _bare_renderer_with_font()
    window = pygame.Surface((400, 400), pygame.SRCALPHA)
    boss = Boss(enemy_registry.get("slime_king"), 0, 0)

    before = pygame.image.tostring(window, "RGBA")
    renderer._draw_entity_health_bar(window, boss, screen_x=100, screen_y=200, width=40)
    after = pygame.image.tostring(window, "RGBA")

    assert before == after  # true no-op for a boss


def test_entity_health_bar_ratio_reflects_current_health():
    renderer = _bare_renderer_with_font()
    window = pygame.Surface((400, 400), pygame.SRCALPHA)
    enemy = Enemy(enemy_registry.get("crawler"), 0, 0)
    enemy.health = enemy.max_health * 0.5

    renderer._draw_entity_health_bar(window, enemy, screen_x=50, screen_y=200, width=60)

    bar_y = 200 - 8
    # Right half of the bar's width should be background (empty), not the filled color.
    right_edge_color = window.get_at((50 + 59, bar_y + 2))[:3]
    assert right_edge_color != HEALTH_FG
