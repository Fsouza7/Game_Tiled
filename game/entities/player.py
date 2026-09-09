"""Player entity: movement, gravity, tile collision, health, mining."""
import logging
from typing import Optional, Tuple

from game.entities.entity import Entity
from game.entities import tile_collision
from game.inventory.inventory import Inventory
from game.inventory.equipment import Equipment
from game.items import item_registry
from game.settings import (
    TILE_SIZE, PLAYER_WIDTH_TILES, PLAYER_HEIGHT_TILES, GRAVITY,
    MAX_FALL_SPEED, PLAYER_MOVE_SPEED, PLAYER_JUMP_VELOCITY,
    PLAYER_MAX_JUMPS, PLAYER_DOUBLE_JUMP_VELOCITY, PLAYER_DOUBLE_JUMP_VISUAL_DURATION_S,
    FALL_DAMAGE_MIN_SPEED, FALL_DAMAGE_PER_UNIT, PLAYER_MAX_HEALTH,
    PLAYER_REACH_TILES, PLAYER_MINE_TICK_S, WORLD_WIDTH_TILES,
    PLAYER_HIT_INVULNERABILITY_S, PLAYER_REGEN_RATE_HP_PER_S,
    PLAYER_REGEN_DELAY_AFTER_DAMAGE_S, FAN_RANGE_TILES,
)
from game.entities import character_registry
from game.world.world import World
from game.world import tile_registry

logger = logging.getLogger(__name__)


class Player(Entity):
    def __init__(self, spawn_x_px: float, spawn_y_px: float, character_id: str = character_registry.DEFAULT_CHARACTER_ID):
        width = PLAYER_WIDTH_TILES * TILE_SIZE
        height = PLAYER_HEIGHT_TILES * TILE_SIZE
        super().__init__(spawn_x_px, spawn_y_px, width, height)

        self.character_id = character_id
        self.spawn_x = spawn_x_px
        self.spawn_y = spawn_y_px
        self.on_ground = False
        self.facing_right = True

        self.max_health = PLAYER_MAX_HEALTH
        self.health = self.max_health
        self.alive = True

        self.inventory = Inventory()
        self.inventory.add_item("wood_pickaxe", 1)
        self.equipment = Equipment()

        # Item ids the player has ever obtained (mined/looted/crafted), even
        # if none are currently in the bag -- drives which recipes are
        # "discovered" in the crafting screen (see crafting_system.is_recipe_discovered).
        # Permanent: never cleared by respawn/death.
        self.discovered_item_ids = {"wood_pickaxe"}

        self._mining_target: Optional[Tuple[int, int]] = None
        self._mining_progress = 0.0
        self._mine_tick_accum = 0.0

        self.invulnerability_remaining = 0.0
        self.attack_cooldown_remaining = 0.0
        self.melee_swing_timer = 0.0
        self.melee_swing_aim = (1.0, 0.0)
        self.regen_delay_remaining = 0.0

        self.jump_count = 0
        self.double_jump_visual_timer = 0.0

    # --- input-facing intent ---
    def move_left(self) -> None:
        self.x_vel = -PLAYER_MOVE_SPEED
        self.facing_right = False

    def move_right(self) -> None:
        self.x_vel = PLAYER_MOVE_SPEED
        self.facing_right = True

    def stop_horizontal(self) -> None:
        self.x_vel = 0.0

    def jump(self) -> None:
        if self.jump_count >= PLAYER_MAX_JUMPS:
            return
        self.y_vel = PLAYER_JUMP_VELOCITY if self.jump_count == 0 else PLAYER_DOUBLE_JUMP_VELOCITY
        self.jump_count += 1
        self.on_ground = False
        if self.jump_count > 1:
            self.double_jump_visual_timer = PLAYER_DOUBLE_JUMP_VISUAL_DURATION_S

    # --- physics ---
    def physics_step(self, world: World, dt: float) -> None:
        if not self.alive:
            return

        self.invulnerability_remaining = max(0.0, self.invulnerability_remaining - dt)
        self.attack_cooldown_remaining = max(0.0, self.attack_cooldown_remaining - dt)
        self.melee_swing_timer = max(0.0, self.melee_swing_timer - dt)
        self.double_jump_visual_timer = max(0.0, self.double_jump_visual_timer - dt)
        self._regen_step(dt)

        self.y_vel = min(self.y_vel + GRAVITY, MAX_FALL_SPEED)

        updraft = self._fan_updraft(world)
        if updraft > 0.0:
            # A Fan's airstream overrides gravity for as long as the player
            # stays inside its range -- a steady push, not an accelerating one.
            self.y_vel = -updraft

        pre_land_y_vel = self.y_vel
        ground_speed_mult = self._ground_speed_multiplier(world) if self.on_ground else 1.0

        tile_collision.move_axis(self, world, self.x_vel * ground_speed_mult, horizontal=True)
        landed_this_frame = tile_collision.move_axis(self, world, self.y_vel, horizontal=False)

        if landed_this_frame:
            bounce_velocity = self._landing_tile_bounce(world)
            if bounce_velocity > 0.0:
                # A trampoline launches the player back up instead of
                # coming to rest -- no fall damage either, same as landing
                # on your feet with a soft cushion.
                self.y_vel = -bounce_velocity
                self.on_ground = False
            else:
                self._apply_fall_damage(pre_land_y_vel)
                self.y_vel = 0.0
                self.on_ground = True
                self.jump_count = 0
        elif self.y_vel < 0:
            self.on_ground = False

        if self.on_ground:
            feet_tile_x = int(self.center_x // TILE_SIZE)
            feet_tile_y = int((self.y + self.height) // TILE_SIZE)
            world.notify_standing_on(feet_tile_x, feet_tile_y, dt)

        self.x = max(0.0, min(self.x, WORLD_WIDTH_TILES * TILE_SIZE - self.width))

    def _landing_tile_bounce(self, world: World) -> float:
        """Returns the bounce_velocity of the tile just beneath the
        player's feet after a landing this frame (0.0 for ordinary ground)."""
        tile_x = int(self.center_x // TILE_SIZE)
        tile_y = int((self.y + self.height) // TILE_SIZE)
        return tile_registry.get(world.get_tile(tile_x, tile_y)).bounce_velocity

    def _ground_speed_multiplier(self, world: World) -> float:
        """TileDef.speed_multiplier of the tile just beneath the player's
        feet (Sand/Mud slow movement, Ice speeds it up); 1.0 on ordinary
        ground. Only applied while on_ground -- doesn't affect air control."""
        tile_x = int(self.center_x // TILE_SIZE)
        tile_y = int((self.y + self.height) // TILE_SIZE)
        return tile_registry.get(world.get_tile(tile_x, tile_y)).speed_multiplier

    def _fan_updraft(self, world: World) -> float:
        """Returns the strongest upward push (px/tick) from any Fan tile
        below the player within FAN_RANGE_TILES in its own column, tapering
        linearly to 0 at max range. 0.0 if no Fan is in range."""
        tile_x = int(self.center_x // TILE_SIZE)
        feet_tile_y = int((self.y + self.height) // TILE_SIZE)
        max_range = int(FAN_RANGE_TILES) + 1
        strongest = 0.0
        for ty in range(feet_tile_y, feet_tile_y - max_range, -1):
            tile_def = tile_registry.get(world.get_tile(tile_x, ty))
            if tile_def.updraft_velocity <= 0.0:
                continue
            distance_tiles = feet_tile_y - ty
            if distance_tiles > FAN_RANGE_TILES:
                continue
            strength = tile_def.updraft_velocity * (1.0 - distance_tiles / (FAN_RANGE_TILES + 1))
            strongest = max(strongest, strength)
        return strongest

    def is_invulnerable(self) -> bool:
        return self.invulnerability_remaining > 0.0

    def can_attack(self) -> bool:
        return self.attack_cooldown_remaining <= 0.0

    def is_regenerating(self) -> bool:
        return self.regen_delay_remaining <= 0.0 and self.health < self.max_health

    def _regen_step(self, dt: float) -> None:
        self.regen_delay_remaining = max(0.0, self.regen_delay_remaining - dt)
        if self.regen_delay_remaining <= 0.0 and self.health < self.max_health:
            self.health = min(self.max_health, self.health + PLAYER_REGEN_RATE_HP_PER_S * dt)

    def _apply_fall_damage(self, impact_speed: float) -> None:
        if impact_speed <= FALL_DAMAGE_MIN_SPEED:
            return
        damage = (impact_speed - FALL_DAMAGE_MIN_SPEED) * FALL_DAMAGE_PER_UNIT
        self.take_damage(damage)

    def take_damage(self, amount: float) -> None:
        if not self.alive:
            return
        self.health -= amount
        self.regen_delay_remaining = PLAYER_REGEN_DELAY_AFTER_DAMAGE_S
        logger.info("Player took %.1f damage (hp=%.1f)", amount, self.health)
        if self.health <= 0:
            self.health = 0
            self.die()

    def die(self) -> None:
        self.alive = False
        logger.info("Player died, respawning")
        self.respawn()

    def respawn(self) -> None:
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.x_vel = 0.0
        self.y_vel = 0.0
        self.health = self.max_health
        self.alive = True
        self._mining_target = None
        self._mining_progress = 0.0
        self.invulnerability_remaining = PLAYER_HIT_INVULNERABILITY_S
        self.attack_cooldown_remaining = 0.0
        self.melee_swing_timer = 0.0
        self.regen_delay_remaining = 0.0
        self.jump_count = 0
        self.double_jump_visual_timer = 0.0

    # --- item discovery ---
    def collect_item(self, item_id: str, quantity: int) -> int:
        """Adds to the inventory and permanently marks item_id as
        discovered (see discovered_item_ids) -- use this instead of
        inventory.add_item directly for anything the player picks up
        (mining drops, enemy loot), so recipe discovery tracks what's
        actually been obtained. Returns whatever add_item returns
        (leftover that didn't fit)."""
        self.discovered_item_ids.add(item_id)
        return self.inventory.add_item(item_id, quantity)

    # --- consumables ---
    def eat_selected(self) -> bool:
        """Eats the selected hotbar item if it's food (heal_amount > 0).
        No-ops at full health so a consumable isn't wasted, and no-ops for
        anything that isn't edible (e.g. `arrow` is CONSUMABLE but not
        food). Returns True iff something was actually eaten."""
        if self.health >= self.max_health:
            return False
        selected = self.inventory.get_selected_item()
        if selected is None:
            return False
        item_def = item_registry.get(selected.item_id)
        if item_def.heal_amount <= 0.0:
            return False
        self.health = min(self.max_health, self.health + item_def.heal_amount)
        self.inventory.remove_from_selected(1)
        return True

    # --- mining ---
    def mining_power_against(self, tile_id: int) -> float:
        tile_def = tile_registry.get(tile_id)
        selected = self.inventory.get_selected_item()
        base_power = 1.0 if tile_def.required_tool is None else 0.0
        if selected is not None:
            item_def = item_registry.get(selected.item_id)
            if item_def.is_tool and (
                tile_def.required_tool is None
                or item_def.tool_type == tile_def.required_tool
            ):
                base_power = max(base_power, item_def.mining_power)
        return base_power

    def is_in_reach(self, tile_x: int, tile_y: int) -> bool:
        dx = (tile_x + 0.5) * TILE_SIZE - self.center_x
        dy = (tile_y + 0.5) * TILE_SIZE - self.center_y
        distance_tiles = (dx ** 2 + dy ** 2) ** 0.5 / TILE_SIZE
        return distance_tiles <= PLAYER_REACH_TILES

    def blocked_mining_reason(self, world: World, tile_x: int, tile_y: int) -> Optional[str]:
        """A human-readable reason the tile at (tile_x, tile_y) can't be
        mined with the currently selected item right now -- specifically
        the "wrong/missing tool" case (e.g. "Requires a Pickaxe"), for
        InputHandler to surface as an on-screen message. None if it's
        minable, or isn't even a breakable/tool-gated tile, or is out of
        reach (those aren't this message's job)."""
        if not self.is_in_reach(tile_x, tile_y):
            return None
        tile_id = world.get_tile(tile_x, tile_y)
        tile_def = tile_registry.get(tile_id)
        if not tile_def.can_break or tile_def.required_tool is None:
            return None
        if self.mining_power_against(tile_id) > 0:
            return None
        return f"Requires a {tile_def.required_tool.capitalize()}"

    def try_mine(self, world: World, tile_x: int, tile_y: int, dt: float) -> Optional[str]:
        """Call every frame the mine button is held. Returns a dropped item
        id the moment the block breaks, otherwise None."""
        if not self.is_in_reach(tile_x, tile_y):
            self._mining_target = None
            return None

        tile_id = world.get_tile(tile_x, tile_y)
        tile_def = tile_registry.get(tile_id)
        if not tile_def.can_break:
            self._mining_target = None
            return None

        power = self.mining_power_against(tile_id)
        if power <= 0:
            self._mining_target = None
            return None

        target = (tile_x, tile_y)
        if self._mining_target != target:
            self._mining_target = target
            self._mining_progress = 0.0
            self._mine_tick_accum = 0.0

        self._mine_tick_accum += dt
        if self._mine_tick_accum < PLAYER_MINE_TICK_S:
            return None
        self._mine_tick_accum = 0.0

        self._mining_progress += power
        if self._mining_progress < tile_def.resistance:
            return None

        drop = world.try_break_tile(tile_x, tile_y)
        self._mining_target = None
        self._mining_progress = 0.0
        return drop

    def cancel_mining(self) -> None:
        self._mining_target = None
        self._mining_progress = 0.0
