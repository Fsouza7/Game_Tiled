"""Headless tests for the Summoner class: class/summon registries, the
weapon_class gate in combat_system.try_attack, casting/replacing a summon
via InputHandler, summon AI targeting + combat_system.resolve_summon_attacks
dealing damage, the class-select screen's input handling, and a full
GameApp smoke test through the two select screens.
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH
from game.entities.player import Player
from game.entities.enemy import Enemy
from game.entities import enemy_registry, class_registry, summon_registry, summon_ai
from game.entities.summon import Summon
from game.combat import combat_system
from game.crafting import recipe_registry
from game.items import item_registry
from game.world.world import World
from game.world.tile_registry import STONE_ID
from game.core.camera import Camera
from game.core.notifications import NotificationQueue
from game.input.input_handler import InputHandler
from game.rendering.renderer import class_card_rect


def _make_world_and_player(class_id="warrior"):
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE, class_id=class_id)
    return world, player


def _spawn_summon_centered_on(summon_def, center_x, center_y) -> Summon:
    """Summon(x, y) takes a top-left corner like every Entity -- mirrors
    combat_system._try_summon_cast's centering so tests that construct a
    Summon directly don't spawn it partly underground/off-center."""
    spawn_x = center_x - (summon_def.width_tiles * TILE_SIZE) / 2
    spawn_y = center_y - (summon_def.height_tiles * TILE_SIZE) / 2
    return Summon(summon_def, spawn_x, spawn_y)


# --- registry sanity ---

def test_class_registry_has_warrior_and_summoner():
    classes = {c.id: c for c in class_registry.all_classes()}
    assert set(classes) == {"warrior", "summoner"}
    assert classes["warrior"].allowed_weapon_classes == ("normal",)
    assert classes["summoner"].allowed_weapon_classes == ("summon",)
    assert classes["summoner"].starting_item_id == "summon_rod_wood"
    assert class_registry.DEFAULT_CLASS_ID == "warrior"


def test_summon_registry_has_both_tiers():
    summons = {s.id: s for s in summon_registry.all_summons()}
    assert set(summons) == {"twig_sprite", "iron_guardian"}
    assert summons["iron_guardian"].damage > summons["twig_sprite"].damage


def test_summon_rod_items_reference_real_summons():
    for item_id in ("summon_rod_wood", "summon_rod_iron"):
        item_def = item_registry.get(item_id)
        assert item_def.is_weapon
        assert item_def.weapon_class == "summon"
        summon_registry.get(item_def.summons_id)  # raises if missing


def test_summon_rod_recipes_are_registered():
    wood = recipe_registry.get("summon_rod_wood")
    iron = recipe_registry.get("summon_rod_iron")
    assert wood.result_item_id == "summon_rod_wood"
    assert wood.station_tile_id is None  # remakeable anywhere, like wood_pickaxe
    assert iron.result_item_id == "summon_rod_iron"
    assert iron.station_tile_id is not None  # workbench-gated


# --- Player.blocked_weapon_class_reason ---

def test_warrior_is_not_blocked_from_a_sword():
    _, player = _make_world_and_player("warrior")
    player.inventory.slots[0].item_id = "wood_sword"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    assert player.blocked_weapon_class_reason() is None


def test_warrior_is_blocked_from_a_summon_rod():
    _, player = _make_world_and_player("warrior")
    player.inventory.slots[1].item_id = "summon_rod_wood"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)
    assert player.blocked_weapon_class_reason() is not None


def test_summoner_is_blocked_from_a_sword_but_not_a_rod():
    _, player = _make_world_and_player("summoner")
    player.inventory.slots[0].item_id = "wood_sword"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    assert player.blocked_weapon_class_reason() is not None

    player.inventory.slots[1].item_id = "summon_rod_wood"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)
    assert player.blocked_weapon_class_reason() is None


# --- combat_system.try_attack class gate + summon casting ---

def test_warrior_attacks_normally_with_a_sword():
    world, player = _make_world_and_player("warrior")
    player.inventory.slots[0].item_id = "wood_sword"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)
    start_health = enemy.health

    result = combat_system.try_attack(player, world, [enemy], (player.center_x + 1, player.center_y))
    assert result is None  # melee hits apply directly, nothing returned
    assert enemy.health < start_health


def test_warrior_cannot_cast_a_summon_rod():
    world, player = _make_world_and_player("warrior")
    player.inventory.slots[1].item_id = "summon_rod_wood"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)

    result = combat_system.try_attack(player, world, [], (player.center_x, player.center_y))
    assert result is None


def test_summoner_casts_starting_rod_and_gets_a_matching_summon():
    world, player = _make_world_and_player("summoner")
    player.inventory.slots[1].item_id = "summon_rod_wood"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)

    result = combat_system.try_attack(player, world, [], (player.center_x, player.center_y))
    assert isinstance(result, Summon)
    assert result.summon_def.id == "twig_sprite"


def test_summoner_cannot_swing_a_sword():
    world, player = _make_world_and_player("summoner")
    player.inventory.slots[0].item_id = "wood_sword"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)
    enemy = Enemy(enemy_registry.get("slime"), player.center_x + TILE_SIZE * 0.5, player.center_y)
    start_health = enemy.health

    result = combat_system.try_attack(player, world, [enemy], (player.center_x + 1, player.center_y))
    assert result is None
    assert enemy.health == start_health  # blocked -- no melee hit landed


# --- casting/replacing a summon via InputHandler (full click path) ---

class _FakeAttackGameApp:
    """Just enough surface for InputHandler._handle_attack_click."""
    def __init__(self, player, world):
        self.player = player
        self.world = world
        self.enemies = []
        self.projectiles = []
        self.summons = []
        self.paused = False
        self.camera = Camera()
        self.notifications = NotificationQueue()


def test_attack_click_casts_a_summon_and_a_better_rod_replaces_it():
    world, player = _make_world_and_player("summoner")
    player.inventory.slots[1].item_id = "summon_rod_wood"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)

    app = _FakeAttackGameApp(player, world)
    pos = app.camera.world_to_screen(player.center_x, player.center_y)

    InputHandler()._handle_attack_click(pos, app)
    assert len(app.summons) == 1
    assert app.summons[0].summon_def.id == "twig_sprite"

    player.attack_cooldown_remaining = 0.0  # bypass the cast cooldown for the test
    player.inventory.slots[2].item_id = "summon_rod_iron"
    player.inventory.slots[2].quantity = 1
    player.inventory.select_hotbar(2)

    InputHandler()._handle_attack_click(pos, app)
    assert len(app.summons) == 1  # replaced, not stacked
    assert app.summons[0].summon_def.id == "iron_guardian"


def test_attack_click_with_a_disallowed_weapon_pushes_a_notification_and_does_nothing():
    world, player = _make_world_and_player("warrior")
    player.inventory.slots[1].item_id = "summon_rod_wood"
    player.inventory.slots[1].quantity = 1
    player.inventory.select_hotbar(1)

    app = _FakeAttackGameApp(player, world)
    pos = app.camera.world_to_screen(player.center_x, player.center_y)

    InputHandler()._handle_attack_click(pos, app)
    assert app.summons == []
    app.notifications.update(0.0)
    assert app.notifications.current_text is not None


# --- summon AI + combat_system.resolve_summon_attacks ---

def test_summon_chases_a_nearby_enemy_and_damages_it_over_time():
    # High in open air (well above the surface), same precedent as
    # test_phase4_combat.py's flying-enemy tests -- keeps nearby terrain
    # out of the way so the flying summon's path to the enemy isn't blocked.
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    air_y = (world.surface_spawn_y(x) - 6) * TILE_SIZE
    player = Player(x * TILE_SIZE, air_y, class_id="summoner")
    summon = _spawn_summon_centered_on(summon_registry.get("twig_sprite"), player.center_x, player.center_y)
    enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, air_y)
    summons = [summon]
    enemies = [enemy]
    start_health = enemy.health

    for _ in range(180):  # 3 simulated seconds
        summon_ai.update(summon, world, player, enemies, dt=1 / 60)
        combat_system.resolve_summon_attacks(player, summons, enemies)

    assert enemy.health < start_health


def test_summon_climbs_over_a_wall_instead_of_getting_stuck_against_it():
    """Regression test: flying straight at its target with no wall-
    routing logic used to mean the summon just pressed into any wall/
    ledge directly in the way, forever, instead of rising up and over it
    -- what the user reported as the summon "having problems" on uneven
    terrain, the same underlying issue as enemy_ai's flying enemies."""
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    air_y = (world.surface_spawn_y(x) - 6) * TILE_SIZE

    wall_x = x + 3
    chunk = world.get_or_create_chunk(world.chunk_index_for(wall_x))
    air_row = int(air_y // TILE_SIZE)
    for dy in range(-5, 6):
        chunk.set_tile(wall_x % CHUNK_WIDTH, air_row + dy, STONE_ID)

    player = Player(x * TILE_SIZE, air_y, class_id="summoner")
    summon = _spawn_summon_centered_on(summon_registry.get("twig_sprite"), player.center_x, player.center_y)
    enemy = Enemy(enemy_registry.get("slime"), (x + 8) * TILE_SIZE, air_y)
    enemies = [enemy]

    start_x = summon.x
    min_y = summon.y
    for _ in range(240):
        summon_ai.update(summon, world, player, enemies, dt=1 / 60)
        min_y = min(min_y, summon.y)

    assert summon.x > start_x + TILE_SIZE * 2  # made real progress, not stuck at the wall
    # Checks the *lowest y it ever reached*, not just where it is at frame
    # 240: once past the wall it closes in on the stationary enemy (which
    # sits back at air_y) and settles into a small orbit around it with no
    # attack-range standoff of its own, so the final-frame y alone is a
    # coin flip on which side of air_y that orbit happens to land on.
    assert min_y < air_y - TILE_SIZE * 3  # climbed well above its start altitude to get over it


def test_summon_hovers_near_player_with_no_enemies_around():
    world, player = _make_world_and_player("summoner")
    summon = _spawn_summon_centered_on(summon_registry.get("twig_sprite"), player.center_x, player.center_y)

    for _ in range(60):
        summon_ai.update(summon, world, player, [], dt=1 / 60)

    distance_tiles = ((summon.center_x - player.center_x) ** 2 + (summon.center_y - player.center_y) ** 2) ** 0.5 / TILE_SIZE
    assert distance_tiles <= summon.summon_def.follow_distance_tiles


# --- class-select screen input handling ---

class _FakeSelectGameApp:
    def __init__(self, player):
        self.player = player
        self.class_select_open = True
        self.granted = False

    def grant_class_starting_item(self):
        self.granted = True
        class_def = class_registry.get(self.player.class_id)
        if class_def.starting_item_id is not None:
            self.player.collect_item(class_def.starting_item_id, 1)


def test_class_select_click_then_confirm_grants_the_starting_item():
    player = Player(0, 0)  # defaults to warrior
    app = _FakeSelectGameApp(player)
    handler = InputHandler()

    classes = class_registry.all_classes()
    summoner_index = next(i for i, c in enumerate(classes) if c.id == "summoner")
    click_pos = class_card_rect(summoner_index).center
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)
    handler._handle_class_select_event(click_event, app)
    assert player.class_id == "summoner"

    confirm_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    handler._handle_class_select_event(confirm_event, app)

    assert app.class_select_open is False
    assert app.granted is True
    assert player.inventory.count_item("summon_rod_wood") == 1


# --- full app boot through both select screens ---

def test_game_app_boots_through_class_select_and_summoner_can_summon():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        assert app.title_open is True
        assert app.character_select_open is False
        assert app.class_select_open is False  # title comes first, then character, then class
        for _ in range(3):
            app.step(dt=1 / 60)

        app.title_open = False
        app.character_select_open = False
        app.class_select_open = True
        app.player.class_id = "summoner"
        app.grant_class_starting_item()
        app.class_select_open = False

        assert app.player.inventory.count_item("summon_rod_wood") == 1

        for _ in range(5):
            app.step(dt=1 / 60)

        player = app.player
        selected_slot = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "summon_rod_wood")
        player.inventory.select_hotbar(selected_slot)
        pos = app.camera.world_to_screen(player.center_x, player.center_y)
        app.input_handler._handle_attack_click(pos, app)

        assert len(app.summons) == 1
        assert app.summons[0].summon_def.id == "twig_sprite"

        for _ in range(5):
            app.step(dt=1 / 60)
    finally:
        pygame.quit()
