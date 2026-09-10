"""Headless tests for game/core/sfx.py: procedurally synthesized sound
effects (no audio files, no numpy -- see the module docstring).
"""
import array

import pygame  # noqa: F401  (import order matters: after conftest sets SDL_VIDEODRIVER)

from game.core import sfx


def setup_function(_):
    # sfx caches synthesized bytes at module scope (see sfx.py's own
    # docstring for why) -- reset it so each test observes a clean build,
    # independent of whatever earlier tests in the suite already did.
    sfx._sound_bytes = {}


# --- waveform builders ---

def test_tone_produces_the_requested_sample_count_within_int16_range():
    samples = sfx._tone(440.0, 0.1, volume=0.5, wave="sine")
    assert len(samples) == int(sfx.SAMPLE_RATE * 0.1)
    assert all(-32768 <= s <= 32767 for s in samples)
    assert any(s != 0 for s in samples)  # actually produced a waveform, not silence


def test_tone_envelope_fades_in_and_out_instead_of_clicking():
    samples = sfx._tone(440.0, 0.1, volume=0.9, wave="square")
    # A raw square wave swings to +/-full amplitude immediately; the
    # envelope should keep the very first and last samples much quieter
    # than the peak amplitude reached mid-tone.
    peak = max(abs(s) for s in samples)
    assert abs(samples[0]) < peak * 0.5
    assert abs(samples[-1]) < peak * 0.5


def test_sweep_moves_from_start_to_end_frequency():
    # A sweep from a very low to a very high frequency should complete
    # far more wave cycles (zero-crossings) than a flat tone at the start
    # frequency over the same duration.
    swept = sfx._sweep(50.0, 4000.0, 0.2, volume=0.8, wave="sine")
    flat = sfx._tone(50.0, 0.2, volume=0.8, wave="sine")

    def _zero_crossings(samples):
        return sum(1 for a, b in zip(samples, samples[1:]) if (a >= 0) != (b >= 0))

    assert _zero_crossings(swept) > _zero_crossings(flat) * 2


def test_noise_burst_is_not_a_pure_tone():
    burst = sfx._noise_burst(0.1, volume=0.6, seed=42)
    assert len(burst) == int(sfx.SAMPLE_RATE * 0.1)
    # White noise has far more sign changes than any smooth tone could.
    crossings = sum(1 for a, b in zip(burst, burst[1:]) if (a >= 0) != (b >= 0))
    assert crossings > len(burst) * 0.3


def test_noise_burst_is_deterministic_for_the_same_seed():
    a = sfx._noise_burst(0.05, volume=0.5, seed=7)
    b = sfx._noise_burst(0.05, volume=0.5, seed=7)
    assert list(a) == list(b)


def test_concat_appends_samples_in_order():
    a = array.array("h", [1, 2, 3])
    b = array.array("h", [4, 5])
    assert list(sfx._concat(a, b)) == [1, 2, 3, 4, 5]


def test_mix_sums_and_clamps_to_int16_range():
    a = array.array("h", [20000, -20000, 100])
    b = array.array("h", [20000, -20000, -50])
    mixed = sfx._mix(a, b)
    assert list(mixed) == [32767, -32768, 50]  # summed then clamped where it overflows


def test_mix_pads_shorter_inputs_with_silence():
    a = array.array("h", [10, 10, 10, 10])
    b = array.array("h", [5, 5])
    mixed = sfx._mix(a, b)
    assert list(mixed) == [15, 15, 10, 10]


def test_duplicate_channels_stereo_duplicates_each_sample_into_both_channels():
    mono = array.array("h", [10, -20, 30])
    stereo = sfx._duplicate_channels(mono, channels=2)
    assert list(stereo) == [10, 10, -20, -20, 30, 30]


def test_duplicate_channels_mono_is_a_passthrough():
    mono = array.array("h", [10, -20, 30])
    assert list(sfx._duplicate_channels(mono, channels=1)) == [10, -20, 30]


def test_duplicate_channels_surround_interleaves_n_copies():
    mono = array.array("h", [10, -20])
    out = sfx._duplicate_channels(mono, channels=4)
    assert list(out) == [10, 10, 10, 10, -20, -20, -20, -20]


def test_output_channels_reads_the_live_mixer_and_defaults_to_2():
    pygame.init()
    try:
        actual = pygame.mixer.get_init()[2]
        assert sfx._output_channels() == actual
    finally:
        pygame.quit()
    assert sfx._output_channels() == 2  # no live mixer -- falls back to stereo


# --- the sound bank ---

def test_build_sound_bank_covers_every_effect_key_with_nonempty_audio():
    bank = sfx._build_sound_bank()
    expected_keys = {
        "mine_tick", "mine_break", "melee_swing", "ranged_shoot",
        "hit_player", "hit_enemy", "craft_complete", "smelt_complete",
        "level_up", "chest_open",
    }
    assert set(bank) == expected_keys
    for key, samples in bank.items():
        assert len(samples) > 0, f"{key} produced no samples"


# --- init/play lifecycle ---

def test_init_populates_sound_bytes_for_every_key():
    pygame.init()
    try:
        sfx.init()
        assert set(sfx._sound_bytes) == set(sfx._build_sound_bank())
        assert all(len(data) > 0 for data in sfx._sound_bytes.values())
    finally:
        pygame.quit()


def test_init_is_idempotent_and_does_not_resynthesize():
    pygame.init()
    try:
        sfx.init()
        first = sfx._sound_bytes
        sfx.init()
        assert sfx._sound_bytes is first  # same dict object -- genuinely skipped, not just equal content
    finally:
        pygame.quit()


def test_play_unknown_key_is_a_silent_noop():
    pygame.init()
    try:
        sfx.init()
        sfx.play("not_a_real_sound_effect")  # must not raise
    finally:
        pygame.quit()


def test_play_without_init_is_a_silent_noop():
    sfx._sound_bytes = {}
    sfx.play("mine_tick")  # nothing synthesized yet -- must not raise


def test_play_with_no_active_mixer_session_is_a_silent_noop():
    pygame.init()
    try:
        sfx.init()
        assert sfx._sound_bytes  # bytes exist
    finally:
        pygame.quit()
    assert not pygame.mixer.get_init()
    sfx.play("mine_tick")  # mixer torn down -- must not raise or crash
    pygame.init()  # leave pygame initialized for whatever runs next


def test_play_survives_a_pygame_quit_and_reinit_cycle_without_crashing():
    """Regression test for a real crash found in this session: playing a
    *cached Sound object* built against an old mixer session, after that
    session was torn down by pygame.quit() (exactly what happens between
    tests elsewhere in this suite that each construct their own GameApp),
    is a native use-after-free -- an access violation that takes the
    whole test process down, not a catchable Python exception. sfx.play()
    must never cache a Sound object across a quit/reinit boundary (see
    the module docstring) -- only the plain bytes, which have no such
    binding."""
    pygame.init()
    try:
        sfx.init()
        sfx.play("chest_open")  # a real, valid mixer session -- should actually play

        pygame.quit()
        sfx.play("chest_open")  # torn-down session -- must degrade to silence, not crash

        pygame.init()
        sfx.play("chest_open")  # fresh session -- must work again, not use a stale object
    finally:
        pygame.quit()


def test_game_app_boot_calls_sfx_init():
    from game.core.game_app import GameApp

    sfx._sound_bytes = {}
    app = GameApp(seed=1)
    try:
        assert sfx._sound_bytes  # GameApp.__init__ called sfx.init()
    finally:
        pygame.quit()


# --- gameplay hook wiring (does the right call site request the right
# key, not "does the resulting audio sound correct") ---

def _make_world_and_player():
    from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE
    from game.entities.player import Player
    from game.world.world import World

    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player, x, surface_y


def test_mining_plays_tick_then_break(monkeypatch):
    from game.entities import player as player_module
    from game.entities.player import Player
    from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES, BEDROCK_ROWS, TILE_SIZE
    from game.world.world import World
    from game.world.tile_registry import STONE_ID

    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    stone_y = None
    for y in range(surface_y + 12, WORLD_HEIGHT_TILES - BEDROCK_ROWS):
        if world.get_tile(x, y) == STONE_ID:
            stone_y = y
            break
    assert stone_y is not None
    # Stone (resistance 2.5) with the starter wood pickaxe (power 1.5)
    # needs 2 ticks -- unlike dirt, which breaks in a single tick and
    # would never exercise the "tick" sound at all.
    player = Player(x * TILE_SIZE, stone_y * TILE_SIZE)
    played = []
    monkeypatch.setattr(player_module.sfx, "play", lambda key: played.append(key))

    drop = None
    for _ in range(200):
        drop = player.try_mine(world, x, stone_y, dt=1.0)  # 1 tick per call at real settings
        if drop is not None:
            break
    assert drop is not None
    assert played[-1] == "mine_break"
    assert "mine_tick" in played[:-1]  # at least one tick before the final break


def test_melee_attack_plays_swing_sound(monkeypatch):
    from game.combat import combat_system

    world, player, x, surface_y = _make_world_and_player()
    player.inventory.add_item("wood_sword", 1)
    player.inventory.select_hotbar(1)
    played = []
    monkeypatch.setattr(combat_system.sfx, "play", lambda key: played.append(key))

    combat_system.try_attack(player, world, [], (player.center_x + 50, player.center_y))
    assert "melee_swing" in played


def test_ranged_attack_plays_shoot_sound(monkeypatch):
    from game.combat import combat_system

    world, player, x, surface_y = _make_world_and_player()
    player.inventory.add_item("wood_bow", 1)
    player.inventory.add_item("arrow", 5)
    player.inventory.select_hotbar(1)
    played = []
    monkeypatch.setattr(combat_system.sfx, "play", lambda key: played.append(key))

    result = combat_system.try_attack(player, world, [], (player.center_x + 50, player.center_y))
    assert result is not None  # actually fired a projectile
    assert "ranged_shoot" in played


def test_game_app_plays_hit_sounds_for_player_and_enemy(monkeypatch):
    from game.core import game_app as game_app_module
    from game.entities.enemy import Enemy
    from game.entities import enemy_registry
    from game.combat import combat_system
    from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE

    app = game_app_module.GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        x = WORLD_WIDTH_TILES // 2
        surface_y = app.world.surface_spawn_y(x) + 1
        app.player.x, app.player.y = x * TILE_SIZE, (surface_y - 1) * TILE_SIZE
        app.player.inventory.add_item("wood_sword", 1)
        app.player.inventory.select_hotbar(1)
        enemy = Enemy(enemy_registry.get("slime"), (x + 1) * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
        app.enemies = [enemy]

        played = []
        monkeypatch.setattr(game_app_module.sfx, "play", lambda key: played.append(key))

        combat_system.try_attack(app.player, app.world, app.enemies, (enemy.center_x, enemy.center_y))
        app.player.take_damage(10.0)
        app.step(dt=1 / 60)

        assert "hit_enemy" in played
        assert "hit_player" in played
    finally:
        pygame.quit()


def test_game_app_plays_craft_and_smelt_complete_sounds(monkeypatch):
    from game.core import game_app as game_app_module
    from game.crafting import recipe_registry, smelt_registry, crafting_system
    from game.settings import DEFAULT_SEED
    from game.world.tile_registry import FURNACE_ID
    from game.settings import TILE_SIZE, CHUNK_WIDTH

    app = game_app_module.GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        app.player.inventory.add_item("wood", 5)
        played = []
        monkeypatch.setattr(game_app_module.sfx, "play", lambda key: played.append(key))

        recipe = recipe_registry.get("wood_plank_block")
        assert crafting_system.start_craft(recipe, app.player, app.world) is True
        for _ in range(60):
            app.step(dt=1 / 60)
            if app.player.craft_job is None:
                break
        assert "craft_complete" in played

        # Smelting, via a placed furnace.
        tile_x = int(app.player.center_x // TILE_SIZE)
        tile_y = int(app.player.center_y // TILE_SIZE)
        chunk = app.world.get_or_create_chunk(app.world.chunk_index_for(tile_x))
        chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, FURNACE_ID)
        smelt = smelt_registry.get("iron_bar")
        app.player.inventory.add_item(smelt.ore_item_id, smelt.ore_quantity)
        app.player.inventory.add_item(smelt.fuel_item_id, smelt.fuel_quantity)
        assert app.furnace_manager.start_smelt(smelt, app.player.inventory, app.world, app.player.center_x, app.player.center_y) is True
        played.clear()
        for _ in range(int(smelt.smelt_time_s * 60) + 30):
            app.step(dt=1 / 60)
            if not app.furnace_manager.jobs:
                break
        assert "smelt_complete" in played
    finally:
        pygame.quit()


def test_game_app_plays_level_up_sound(monkeypatch):
    from game.core import game_app as game_app_module
    from game.settings import DEFAULT_SEED

    app = game_app_module.GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        played = []
        monkeypatch.setattr(game_app_module.sfx, "play", lambda key: played.append(key))

        app.player.skills.add_xp("mining", 1_000_000.0)  # guaranteed level-up(s)
        app.step(dt=1 / 60)

        assert "level_up" in played
    finally:
        pygame.quit()


def test_opening_a_chest_plays_chest_open_sound(monkeypatch):
    from game.input.input_handler import InputHandler
    from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH
    from game.world.tile_registry import PERSONAL_CHEST_ID
    from game.core.notifications import NotificationQueue
    from game.input import input_handler as input_handler_module

    world, player, x, surface_y = _make_world_and_player()
    chunk = world.get_or_create_chunk(world.chunk_index_for(x))
    chunk.set_tile(x % CHUNK_WIDTH, surface_y - 1, PERSONAL_CHEST_ID)

    class _FakeGameApp:
        def __init__(self):
            self.player = player
            self.world = world
            self.npcs = []
            self.paused = False
            self.inventory_open = False
            self.crafting_open = False
            self.skills_open = False
            self.talking_to = None
            self.npc_shop_open = False
            self.chest_open = False
            self.notifications = NotificationQueue()

        def close_npc_panel(self):
            self.talking_to = None

        def close_chest(self):
            self.chest_open = False

    app = _FakeGameApp()
    played = []
    monkeypatch.setattr(input_handler_module.sfx, "play", lambda key: played.append(key))

    InputHandler()._handle_talk(app)

    assert app.chest_open is True
    assert "chest_open" in played
