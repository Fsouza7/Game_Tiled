"""Owns the game loop and wires world/player/camera/input/renderer together."""
import logging

import pygame

from game.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS,
    TILE_SIZE, DEFAULT_SEED, WORLD_WIDTH_TILES, HITPOINTS_HP_PER_LEVEL,
    CRAFTING_XP_PER_SMELT,
)
from game.world.world import World
from game.world import checkpoints
from game.entities.player import Player
from game.entities import enemy_ai, summon_ai, character_registry, class_registry
from game.entities.enemy_spawner import EnemySpawner
from game.combat import combat_system
from game.crafting import crafting_system
from game.crafting.furnace_system import FurnaceManager
from game.items import item_registry
from game.skills.skills import SKILL_NAMES
from game.core.camera import Camera
from game.core.debug_overlay import DebugOverlay
from game.core.world_clock import WorldClock
from game.core.notifications import NotificationQueue
from game.core import save_system
from game.input.input_handler import InputHandler
from game.rendering.renderer import Renderer
from game.rendering.particles import ParticleSystem
from game.settings import PARTICLE_DUST_STEP_INTERVAL_S

logger = logging.getLogger(__name__)


class GameApp:
    def __init__(self, seed: int = DEFAULT_SEED):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        self.seed = seed
        self.input_handler = InputHandler()
        self.renderer = Renderer()
        self.debug_overlay = DebugOverlay()

        # Shown once at startup; Player already exists with the default
        # skin/class so gameplay systems never have to special-case "no
        # player yet" -- picking a character/class just swaps
        # player.character_id/class_id. Class select follows character
        # select (see step()'s early-return gate below).
        self.character_select_open = True
        self.class_select_open = False
        self.running = True

        self._new_run(seed, character_registry.DEFAULT_CHARACTER_ID, class_registry.DEFAULT_CLASS_ID)

        logger.info("World seed: %d", seed)

    def _new_run(self, seed: int, character_id: str, class_id: str = class_registry.DEFAULT_CLASS_ID) -> None:
        """(Re)builds everything that represents "one playthrough" -- used
        both at startup and by the pause menu's Restart action."""
        self.world = World(seed)
        spawn_x_tile = WORLD_WIDTH_TILES // 2
        spawn_y_tile = self.world.surface_spawn_y(spawn_x_tile)
        self.player = Player(spawn_x_tile * TILE_SIZE, spawn_y_tile * TILE_SIZE, character_id, class_id)
        self.grant_class_starting_item()

        self.camera = Camera()
        self.camera.x = self.player.center_x - self.camera.view_width / 2
        self.camera.y = self.player.center_y - self.camera.view_height / 2

        self.enemies = []
        self.projectiles = []
        self.summons = []
        self.particles = ParticleSystem()
        self.enemy_spawner = EnemySpawner()
        self.world_clock = WorldClock()
        self.furnace_manager = FurnaceManager()
        self.notifications = NotificationQueue()
        self._dust_step_cooldown = 0.0

        self.paused = False
        self.inventory_open = False
        self.crafting_open = False
        self.crafting_scroll_y = 0
        self.settings_open = False
        self.skills_open = False
        self.selected_skill_id = "attack"

    def restart(self) -> None:
        self._new_run(self.seed, self.player.character_id, self.player.class_id)

    def grant_class_starting_item(self) -> None:
        """Grants the player's class starting item, if it has one (e.g.
        Summoner's Twig Rod). Called from _new_run (boot/restart -- the
        player's class_id is already correct there) and from InputHandler
        when the class-select screen is confirmed (class_id was just set
        directly on the player, outside of _new_run)."""
        class_def = class_registry.get(self.player.class_id)
        if class_def.starting_item_id is not None:
            self.player.collect_item(class_def.starting_item_id, 1)

    def save_game(self) -> None:
        # Reads save_system.SAVE_FILE_PATH at call time (not via the
        # function's own default arg, which is bound once at import time)
        # so tests can monkeypatch it to a temp path without touching the
        # real save file.
        save_system.save_to_file(self.world, self.player, self.world_clock, self.furnace_manager, save_system.SAVE_FILE_PATH)
        self.notifications.push("Game saved")
        logger.info("Saved game to %s", save_system.SAVE_FILE_PATH)

    def load_game(self) -> None:
        """Rebuilds world/player/clock/furnace state from disk, discarding
        the current run -- same per-run transient state _new_run already
        resets (enemies, projectiles, particles, spawner) gets reset here
        too, since none of that is persisted (see save_system docstring)."""
        data = save_system.load_from_file(save_system.SAVE_FILE_PATH)
        if data is None:
            self.notifications.push("No save found")
            return

        self.world, self.player, self.world_clock, self.furnace_manager = save_system.deserialize(data)
        self.seed = self.world.seed

        self.camera = Camera()
        self.camera.x = self.player.center_x - self.camera.view_width / 2
        self.camera.y = self.player.center_y - self.camera.view_height / 2

        self.enemies = []
        self.projectiles = []
        self.summons = []
        self.particles = ParticleSystem()
        self.enemy_spawner = EnemySpawner()
        self._dust_step_cooldown = 0.0

        self.paused = False
        self.inventory_open = False
        self.crafting_open = False
        self.crafting_scroll_y = 0
        self.settings_open = False
        self.skills_open = False
        self.selected_skill_id = "attack"

        self.notifications.push("Game loaded")
        logger.info("Loaded game from %s", save_system.SAVE_FILE_PATH)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)
        pygame.quit()

    def step(self, dt: float) -> None:
        events = pygame.event.get()
        self.input_handler.handle_discrete_events(events, self)

        if self.character_select_open or self.class_select_open:
            self.renderer.draw(
                self.window, self.world, self.player, self.camera,
                self.enemies, self.projectiles, self.world_clock, self.particles,
                self.inventory_open, self.crafting_open, self.paused, self.crafting_scroll_y,
                settings_open=self.settings_open,
                character_select_open=self.character_select_open,
                class_select_open=self.class_select_open,
            )
            pygame.display.flip()
            return

        self.input_handler.update_continuous(dt, self)

        if not self.paused:
            self.world_clock.update(dt)
            self.world.update(dt)
            self.world.ensure_chunks_around(self.player.center_x)
            self.player.physics_step(self.world, dt)

            for enemy in self.enemies:
                enemy_ai.update(enemy, self.world, self.player, dt)
            for summon in self.summons:
                summon_ai.update(summon, self.world, self.player, self.enemies, dt)
            combat_system.resolve_contact_damage(self.player, self.enemies)
            combat_system.resolve_hazard_damage(self.player, self.world)
            combat_system.resolve_hazard_feature_damage(self.player, self.world)
            combat_system.resolve_summon_attacks(self.player, self.summons, self.enemies)
            self.projectiles = combat_system.update_projectiles(self.player, self.projectiles, self.world, self.enemies, dt)
            self._collect_enemy_drops()
            self.enemies = [e for e in self.enemies if e.alive]
            self.enemy_spawner.update(dt, self.world, self.player, self.enemies, self.world_clock.is_night)

            self._update_footstep_dust(dt)
            self._handle_checkpoint_activation()
            self._update_furnace(dt)
            self.particles.update(dt)
            self.notifications.update(dt)

            self.camera.follow(self.player.center_x, self.player.center_y)

        self._announce_level_ups()

        self.renderer.draw(
            self.window, self.world, self.player, self.camera,
            self.enemies, self.projectiles, self.world_clock, self.particles,
            self.inventory_open, self.crafting_open, self.paused,
            self.crafting_scroll_y, settings_open=self.settings_open, character_select_open=False,
            furnace_manager=self.furnace_manager, notifications=self.notifications,
            summons=self.summons, skills_open=self.skills_open, selected_skill_id=self.selected_skill_id,
        )
        self.debug_overlay.draw(self.window, self.clock, self.player, self.world, self.camera, self.enemies, self.world_clock)
        pygame.display.flip()

    def _collect_enemy_drops(self) -> None:
        for enemy in self.enemies:
            if enemy.defeated and not enemy.drop_collected:
                enemy.drop_collected = True
                drop = enemy.roll_drop()
                if drop is not None:
                    item_id, quantity = drop
                    self._collect_and_announce(item_id, quantity)

    def _collect_and_announce(self, item_id: str, quantity: int) -> None:
        """Grants an item (mining drop, enemy loot, furnace output) and
        announces any recipe this just fully unlocked (see
        crafting_system.collect_and_discover / "How recipe discovery works" in README)."""
        newly_discovered = crafting_system.collect_and_discover(self.player, item_id, quantity)
        for recipe in newly_discovered:
            self.notifications.push(f"New recipe unlocked: {recipe.name}")

    def _update_furnace(self, dt: float) -> None:
        for item_id, quantity in self.furnace_manager.update(dt):
            self.notifications.push(f"{quantity}x {item_registry.get(item_id).name} ready!")
            self._collect_and_announce(item_id, quantity)
            self.player.skills.add_xp("crafting", CRAFTING_XP_PER_SMELT * self.player.skills.crafting_xp_multiplier())

    def _announce_level_ups(self) -> None:
        for skill_id, level in self.player.skills.drain_level_ups():
            if skill_id == "hitpoints":
                self.player.max_health += HITPOINTS_HP_PER_LEVEL
                self.player.health += HITPOINTS_HP_PER_LEVEL
            self.notifications.push(f"{SKILL_NAMES[skill_id]} level up! Lv {level}")

    def _update_footstep_dust(self, dt: float) -> None:
        self._dust_step_cooldown = max(0.0, self._dust_step_cooldown - dt)
        if not (self.player.on_ground and self.player.x_vel != 0):
            return
        if self._dust_step_cooldown > 0.0:
            return
        self._dust_step_cooldown = PARTICLE_DUST_STEP_INTERVAL_S
        self.particles.spawn_dust(self.player.center_x, self.player.y + self.player.height)

    def _handle_checkpoint_activation(self) -> None:
        if checkpoints.try_activate(self.player, self.world):
            self.particles.spawn_confetti(self.player.center_x, self.player.center_y)
