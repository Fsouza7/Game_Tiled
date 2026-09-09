"""Draws the world, player and HUD. No gameplay logic lives here.

Uses the real art in assets/ (Terrain.png for tiles, NinjaFrog sprites for
the player, a Background tile for the sky) -- see assets.py for exactly
which sprites were picked and why. No third-party assets are used for
gameplay data (tile stats, drops, physics); only the visuals come from
assets/.
"""
from typing import Dict, Optional

import pygame

import math

from game.settings import (
    TILE_SIZE, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES,
    WINDOW_WIDTH, WINDOW_HEIGHT, HOTBAR_SLOTS,
    PLAYER_ANIMATION_FRAME_DELAY, BACKGROUND_PARALLAX,
    MELEE_REACH_TILES, MELEE_ARC_DEGREES, MELEE_SWING_VISUAL_DURATION_S,
    LIGHT_SEARCH_MARGIN_TILES, MAX_DARKNESS_ALPHA,
    TORCH_FLICKER_AMPLITUDE, TORCH_FLICKER_SPEED,
    NIGHT_MIN_AMBIENT, DAY_MAX_AMBIENT, CHARACTER_PORTRAIT_SIZE,
)
from game.world import tile_registry, lighting, hazard_feature
from game.world.tile_registry import AIR_ID, CRUMBLE_PLATFORM_ID, CHECKPOINT_ID
from game.items import item_registry
from game.items.item import ItemCategory, ItemRarity
from game.inventory.equipment import SLOTS as EQUIPMENT_SLOTS
from game.rendering import assets
from game.rendering.particles import DUST, CONFETTI
from game.crafting import recipe_registry, crafting_system, smelt_registry
from game.crafting.recipe import RecipeDef
from game.crafting.smelt_recipe import SmeltRecipeDef
from game.crafting.furnace_system import nearest_station_tile as _nearest_station_tile
from game.entities.enemy_def import AIType
from game.entities import character_registry, class_registry
from game.combat import combat_system
from game.skills.skills import SKILL_IDS, SKILL_NAMES
from game.skills import skill_tree_registry

HUD_BG = (20, 20, 24)
HUD_BORDER = (240, 240, 240)
HUD_SELECTED_BORDER = (255, 210, 60)
HEALTH_BG = (60, 20, 20)
HEALTH_FG = (200, 40, 40)
PANEL_BG = (18, 18, 24, 235)
PANEL_HEADER_BG = (40, 36, 55)
PANEL_BORDER = (90, 84, 110)
ACCENT_GOLD = (215, 180, 90)

# Top-left, always-visible Combat Lv HUD bar (see _draw_combat_level_bar).
COMBAT_LEVEL_BAR_WIDTH = 160
COMBAT_LEVEL_BAR_HEIGHT = 10

# Flat swatch color for items with no dedicated art (see assets.py).
_CATEGORY_SWATCH_COLOR = {
    ItemCategory.TOOL: (220, 200, 60),
    ItemCategory.WEAPON: (150, 160, 180),
    ItemCategory.ARMOR: (70, 120, 120),
    ItemCategory.MATERIAL: (170, 130, 90),
    ItemCategory.CONSUMABLE: (200, 90, 90),
    ItemCategory.ACCESSORY: (150, 110, 200),
}
_DEFAULT_SWATCH_COLOR = (200, 200, 200)

# Slot border color by rarity -- a classic RPG read on item quality that
# costs nothing extra to compute (ItemDef.rarity already exists).
_RARITY_BORDER_COLOR = {
    ItemRarity.COMMON: (140, 140, 148),
    ItemRarity.UNCOMMON: (90, 200, 110),
    ItemRarity.RARE: (90, 150, 235),
    ItemRarity.EPIC: (185, 100, 230),
}

_EQUIPMENT_SLOT_LABELS = {"head": "Head", "body": "Body", "accessory": "Accessory"}

_SKILL_ABBREVIATIONS = {
    "attack": "Atk", "defense": "Def", "magic": "Mag",
    "mining": "Min", "crafting": "Cra", "hitpoints": "HP",
}

# Crafting panel layout -- module-level so input_handler.py can hit-test
# mouse clicks against the exact same geometry used to draw it. A grid of
# icon cells (discovered recipes only -- locked ones don't appear at all,
# see _recipe_sections) on the left, a fixed details panel for whichever
# cell is hovered on the right (see _draw_recipe_details).
CRAFTING_GRID_COLUMNS = 5
CRAFTING_CELL_SIZE = 54
CRAFTING_CELL_GAP = 10
CRAFTING_GRID_WIDTH = CRAFTING_GRID_COLUMNS * CRAFTING_CELL_SIZE + (CRAFTING_GRID_COLUMNS - 1) * CRAFTING_CELL_GAP
CRAFTING_DETAILS_WIDTH = 210
CRAFTING_PANEL_PADDING = 14
CRAFTING_DIVIDER_GAP = 18
CRAFTING_PANEL_WIDTH = CRAFTING_PANEL_PADDING * 2 + CRAFTING_GRID_WIDTH + CRAFTING_DIVIDER_GAP + CRAFTING_DETAILS_WIDTH
CRAFTING_SECTION_HEADER_HEIGHT = 24
CRAFTING_SECTION_GAP = 8
CRAFTING_PANEL_X = (WINDOW_WIDTH - CRAFTING_PANEL_WIDTH) // 2
CRAFTING_PANEL_Y = 70
CRAFTING_TITLE_HEIGHT = 38
# The grid scrolls once content exceeds this, so the panel never grows
# into the hotbar/health HUD as more recipes are added over time.
CRAFTING_VIEWPORT_HEIGHT = 460
CRAFTING_SCROLL_STEP = CRAFTING_CELL_SIZE + CRAFTING_CELL_GAP


# Primary grouping is by what the result *is* (a category a player
# recognizes at a glance), not where it's crafted -- each cell still shows
# its own station requirement in the details panel (see _station_label).
# Smelt recipes (furnace) get their own trailing section since the whole
# interaction (start a timed job, come back later) differs from an
# instant craft even though they share this screen's layout/discovery code.
_CATEGORY_SECTION_ORDER = (
    (ItemCategory.BLOCK, "Building"),
    (ItemCategory.DECORATION, "Structures & Utility"),
    (ItemCategory.TOOL, "Tools"),
    (ItemCategory.WEAPON, "Weapons"),
    (ItemCategory.ARMOR, "Armor"),
    (ItemCategory.ACCESSORY, "Accessories"),
    (ItemCategory.CONSUMABLE, "Ammo"),
    (ItemCategory.MATERIAL, "Materials"),
)


def _station_label(station_tile_id) -> str:
    if station_tile_id is None:
        return "Anywhere"
    return tile_registry.get(station_tile_id).name


def _recipe_sections(discovered_item_ids):
    """Returns [(section_title, [recipes])] grouped by the crafted item's
    category, in a fixed, predictable order, with smelting recipes as
    their own trailing section. Undiscovered recipes (see
    crafting_system.is_recipe_discovered) are left out entirely -- a
    section with nothing discovered in it doesn't appear either."""
    sections = []
    for category, title in _CATEGORY_SECTION_ORDER:
        recipes = [
            r for r in recipe_registry.all_recipes()
            if item_registry.get(r.result_item_id).category == category
            and crafting_system.is_recipe_discovered(r, discovered_item_ids)
        ]
        if recipes:
            sections.append((title, recipes))
    smelt_recipes = [r for r in smelt_registry.all_recipes() if crafting_system.is_recipe_discovered(r, discovered_item_ids)]
    if smelt_recipes:
        sections.append(("Smelting (Furnace)", smelt_recipes))
    return sections


def _crafting_layout(scroll_y, discovered_item_ids):
    """Yields (recipe, cell_rect) for every discovered recipe in on-screen
    grid order (left to right, wrapping every CRAFTING_GRID_COLUMNS),
    accounting for section headers and the current scroll offset -- the
    single source of truth for drawing, click hit-testing and hover
    (details-panel) lookup alike."""
    grid_x = CRAFTING_PANEL_X + CRAFTING_PANEL_PADDING
    y = CRAFTING_PANEL_Y + CRAFTING_TITLE_HEIGHT - scroll_y
    for title, recipes in _recipe_sections(discovered_item_ids):
        if not recipes:
            continue
        y += CRAFTING_SECTION_HEADER_HEIGHT
        col = 0
        for recipe in recipes:
            cell_x = grid_x + col * (CRAFTING_CELL_SIZE + CRAFTING_CELL_GAP)
            rect = pygame.Rect(cell_x, y, CRAFTING_CELL_SIZE, CRAFTING_CELL_SIZE)
            yield recipe, rect
            col += 1
            if col >= CRAFTING_GRID_COLUMNS:
                col = 0
                y += CRAFTING_CELL_SIZE + CRAFTING_CELL_GAP
        if col != 0:  # trailing partial row still occupies its own row
            y += CRAFTING_CELL_SIZE + CRAFTING_CELL_GAP
        y += CRAFTING_SECTION_GAP


def crafting_content_height(discovered_item_ids) -> int:
    """Total height of the recipe grid content, unscrolled/unclipped."""
    last_bottom = CRAFTING_PANEL_Y + CRAFTING_TITLE_HEIGHT
    for _, rect in _crafting_layout(0, discovered_item_ids):
        last_bottom = max(last_bottom, rect.bottom)
    return last_bottom - CRAFTING_PANEL_Y + 12


def crafting_panel_height(discovered_item_ids) -> int:
    return min(crafting_content_height(discovered_item_ids), CRAFTING_TITLE_HEIGHT + CRAFTING_VIEWPORT_HEIGHT)


def crafting_max_scroll(discovered_item_ids) -> int:
    return max(0, crafting_content_height(discovered_item_ids) - crafting_panel_height(discovered_item_ids))


def recipe_at_screen_pos(pos, scroll_y, discovered_item_ids):
    viewport = pygame.Rect(
        CRAFTING_PANEL_X, CRAFTING_PANEL_Y + CRAFTING_TITLE_HEIGHT,
        CRAFTING_PANEL_PADDING + CRAFTING_GRID_WIDTH, crafting_panel_height(discovered_item_ids) - CRAFTING_TITLE_HEIGHT,
    )
    if not viewport.collidepoint(pos):
        return None
    for recipe, rect in _crafting_layout(scroll_y, discovered_item_ids):
        if rect.collidepoint(pos):
            return recipe
    return None


# --- Inventory / equipment panel layout ---
INVENTORY_PANEL_WIDTH = 600
INVENTORY_PANEL_HEIGHT = 580  # tall enough for 3 equipment slots + stats + the skills summary below them
INVENTORY_PANEL_X = (WINDOW_WIDTH - INVENTORY_PANEL_WIDTH) // 2
INVENTORY_PANEL_Y = (WINDOW_HEIGHT - INVENTORY_PANEL_HEIGHT) // 2
INVENTORY_TITLE_HEIGHT = 38
INVENTORY_LEFT_WIDTH = 190
INVENTORY_BAG_COLS = 5
INVENTORY_BAG_SLOT_SIZE = 62
INVENTORY_BAG_GAP = 10
INVENTORY_EQUIP_SLOT_SIZE = 56
ITEM_TOOLTIP_WIDTH = 260
ITEM_TOOLTIP_CURSOR_OFFSET = 18

_EQUIPMENT_SLOT_ORDER = list(EQUIPMENT_SLOTS)


def equipment_slot_rect(slot_name: str) -> pygame.Rect:
    index = _EQUIPMENT_SLOT_ORDER.index(slot_name)
    x = INVENTORY_PANEL_X + (INVENTORY_LEFT_WIDTH - INVENTORY_EQUIP_SLOT_SIZE) // 2
    y = INVENTORY_PANEL_Y + INVENTORY_TITLE_HEIGHT + 130 + index * (INVENTORY_EQUIP_SLOT_SIZE + 16)
    return pygame.Rect(x, y, INVENTORY_EQUIP_SLOT_SIZE, INVENTORY_EQUIP_SLOT_SIZE)


def inventory_bag_slot_rect(index: int) -> pygame.Rect:
    col = index % INVENTORY_BAG_COLS
    row = index // INVENTORY_BAG_COLS
    x = INVENTORY_PANEL_X + INVENTORY_LEFT_WIDTH + 20 + col * (INVENTORY_BAG_SLOT_SIZE + INVENTORY_BAG_GAP)
    y = INVENTORY_PANEL_Y + INVENTORY_TITLE_HEIGHT + 14 + row * (INVENTORY_BAG_SLOT_SIZE + INVENTORY_BAG_GAP)
    return pygame.Rect(x, y, INVENTORY_BAG_SLOT_SIZE, INVENTORY_BAG_SLOT_SIZE)


def equipment_slot_at_screen_pos(pos) -> Optional[str]:
    for slot_name in _EQUIPMENT_SLOT_ORDER:
        if equipment_slot_rect(slot_name).collidepoint(pos):
            return slot_name
    return None


def inventory_bag_index_at_screen_pos(pos, slot_count: int) -> Optional[int]:
    for index in range(slot_count):
        if inventory_bag_slot_rect(index).collidepoint(pos):
            return index
    return None


# --- Skills screen layout: a row list (left, one per SKILL_IDS entry) +
# a fixed node-details panel (right, the selected skill's 3-tier tree,
# nodes stacked vertically and connected by a line so it reads as an
# actual tree to climb, not just a row of boxes) -- same "one function
# builds the rects, drawing and hit-testing both call it" discipline as
# the crafting grid above. ---
SKILLS_PANEL_WIDTH = 640
SKILLS_PANEL_HEIGHT = 520
SKILLS_PANEL_X = (WINDOW_WIDTH - SKILLS_PANEL_WIDTH) // 2
SKILLS_PANEL_Y = (WINDOW_HEIGHT - SKILLS_PANEL_HEIGHT) // 2
SKILLS_TITLE_HEIGHT = 38
SKILLS_ROW_HEIGHT = 46
SKILLS_ROW_GAP = 8
SKILLS_LIST_WIDTH = 260
SKILLS_NODE_WIDTH = 300
SKILLS_NODE_HEIGHT = 104
SKILLS_NODE_GAP = 26
SKILLS_MAX_NODES_PER_SKILL = 3  # every skill's tree is 3 tiers this pass


def skill_row_rect(index: int) -> pygame.Rect:
    x = SKILLS_PANEL_X + 14
    y = SKILLS_PANEL_Y + SKILLS_TITLE_HEIGHT + 14 + index * (SKILLS_ROW_HEIGHT + SKILLS_ROW_GAP)
    return pygame.Rect(x, y, SKILLS_LIST_WIDTH, SKILLS_ROW_HEIGHT)


def skill_index_at_screen_pos(pos) -> Optional[int]:
    for index in range(len(SKILL_IDS)):
        if skill_row_rect(index).collidepoint(pos):
            return index
    return None


def skill_node_rect(index: int) -> pygame.Rect:
    x = SKILLS_PANEL_X + SKILLS_LIST_WIDTH + 40
    y = SKILLS_PANEL_Y + SKILLS_TITLE_HEIGHT + 66 + index * (SKILLS_NODE_HEIGHT + SKILLS_NODE_GAP)
    return pygame.Rect(x, y, SKILLS_NODE_WIDTH, SKILLS_NODE_HEIGHT)


def skill_node_at_screen_pos(pos) -> Optional[int]:
    for index in range(SKILLS_MAX_NODES_PER_SKILL):
        if skill_node_rect(index).collidepoint(pos):
            return index
    return None


# --- Character select screen layout ---
CHARACTER_PORTRAIT_GAP = 24


def character_portrait_rect(index: int) -> pygame.Rect:
    count = len(character_registry.all_characters())
    total_width = count * CHARACTER_PORTRAIT_SIZE + (count - 1) * CHARACTER_PORTRAIT_GAP
    start_x = (WINDOW_WIDTH - total_width) // 2
    x = start_x + index * (CHARACTER_PORTRAIT_SIZE + CHARACTER_PORTRAIT_GAP)
    y = WINDOW_HEIGHT // 2 - CHARACTER_PORTRAIT_SIZE // 2
    return pygame.Rect(x, y, CHARACTER_PORTRAIT_SIZE, CHARACTER_PORTRAIT_SIZE)


def character_index_at_screen_pos(pos) -> Optional[int]:
    for index in range(len(character_registry.all_characters())):
        if character_portrait_rect(index).collidepoint(pos):
            return index
    return None


# --- Class select layout (text cards -- no per-class art exists, unlike
# the character portraits above) ---
CLASS_CARD_WIDTH = 220
CLASS_CARD_HEIGHT = 200
CLASS_CARD_GAP = 40


def class_card_rect(index: int) -> pygame.Rect:
    count = len(class_registry.all_classes())
    total_width = count * CLASS_CARD_WIDTH + (count - 1) * CLASS_CARD_GAP
    start_x = (WINDOW_WIDTH - total_width) // 2
    x = start_x + index * (CLASS_CARD_WIDTH + CLASS_CARD_GAP)
    y = WINDOW_HEIGHT // 2 - CLASS_CARD_HEIGHT // 2
    return pygame.Rect(x, y, CLASS_CARD_WIDTH, CLASS_CARD_HEIGHT)


def class_index_at_screen_pos(pos) -> Optional[int]:
    for index in range(len(class_registry.all_classes())):
        if class_card_rect(index).collidepoint(pos):
            return index
    return None


# --- Pause menu layout ---
PAUSE_BUTTON_SIZE = 56
PAUSE_BUTTON_GAP = 18

_PAUSE_MAIN_ACTIONS = ("play", "settings", "save", "load", "restart", "close")
_PAUSE_SETTINGS_ACTIONS = ("zoom_out", "zoom_in", "back")


def _pause_button_rects(actions) -> Dict[str, pygame.Rect]:
    total_width = len(actions) * PAUSE_BUTTON_SIZE + (len(actions) - 1) * PAUSE_BUTTON_GAP
    start_x = (WINDOW_WIDTH - total_width) // 2
    y = WINDOW_HEIGHT // 2 + 30
    return {
        action: pygame.Rect(start_x + i * (PAUSE_BUTTON_SIZE + PAUSE_BUTTON_GAP), y, PAUSE_BUTTON_SIZE, PAUSE_BUTTON_SIZE)
        for i, action in enumerate(actions)
    }


def pause_menu_button_rects(settings_open: bool) -> Dict[str, pygame.Rect]:
    return _pause_button_rects(_PAUSE_SETTINGS_ACTIONS if settings_open else _PAUSE_MAIN_ACTIONS)


def pause_button_at_screen_pos(pos, settings_open: bool) -> Optional[str]:
    for action, rect in pause_menu_button_rects(settings_open).items():
        if rect.collidepoint(pos):
            return action
    return None


class Renderer:
    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 14)
        self.big_font = pygame.font.SysFont("consolas", 28, bold=True)

        self.tile_textures = assets.load_tile_textures()
        player_frame_size = int(round(TILE_SIZE * 1.8))  # matches PLAYER_HEIGHT_TILES
        self.character_animations = assets.load_all_character_animations(player_frame_size)
        self.background_tile = assets.load_background_tile()
        self.item_icons = assets.load_static_item_icons()

        self.crumble_shake_frames = assets.load_crumble_shake_frames(TILE_SIZE)
        self.checkpoint_active_frames = assets.load_checkpoint_active_frames(TILE_SIZE)
        self.hazard_textures = assets.load_hazard_textures(TILE_SIZE)
        self.particle_textures = assets.load_particle_textures()
        self.shadow_texture = assets.load_shadow_texture()
        self.menu_button_icons = assets.load_menu_button_icons()

        self._scaled_tile_cache = {}
        self._darkness_overlay_cache = {}
        self._anim_counter = 0

        self._sunset_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._sunset_overlay.fill((255, 140, 70, 255))
        self._night_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._night_overlay.fill((10, 10, 35, 255))

    def draw(
        self, window, world, player, camera, enemies, projectiles, world_clock, particles,
        inventory_open: bool, crafting_open: bool, paused: bool, crafting_scroll_y: int = 0,
        *, settings_open: bool = False, character_select_open: bool = False,
        class_select_open: bool = False, furnace_manager=None, notifications=None,
        summons=(), skills_open: bool = False, selected_skill_id: str = "attack",
    ) -> None:
        if character_select_open:
            self._draw_character_select_screen(window, player)
            self._anim_counter += 1
            return
        if class_select_open:
            self._draw_class_select_screen(window, player)
            self._anim_counter += 1
            return

        ambient_light = world_clock.ambient_light
        light_sources = self._gather_light_sources(world, camera)

        self._draw_background(window, camera, world_clock)
        self._draw_world(window, world, camera, light_sources, ambient_light, player)
        self._draw_hazard_features(window, world, camera)
        self._draw_enemies(window, world, enemies, camera, light_sources, ambient_light)
        self._draw_summons(window, summons, camera, light_sources, ambient_light)
        self._draw_projectiles(window, projectiles, camera)
        self._draw_player(window, world, player, camera, light_sources, ambient_light)
        self._draw_particles(window, particles, camera)
        self._draw_melee_swing(window, player, camera)
        self._draw_aim_reticle(window, player)
        self._draw_hook_line(window, player, camera)
        self._draw_health(window, player)
        self._draw_hotbar(window, player.inventory)
        self._draw_combat_level_bar(window, player)
        self._draw_day_night_indicator(window, world_clock)
        if notifications is not None:
            self._draw_notification(window, notifications)
        if inventory_open:
            self._draw_inventory_screen(window, player)
        if crafting_open:
            self._draw_crafting_screen(window, world, player, furnace_manager, crafting_scroll_y)
        if skills_open:
            self._draw_skills_screen(window, player, selected_skill_id)
        if paused:
            self._draw_pause_overlay(window, settings_open)
        self._anim_counter += 1

    def _draw_notification(self, window, notifications) -> None:
        text = notifications.current_text
        if text is None:
            return
        alpha = int(255 * min(1.0, notifications.current_progress * 4))  # quick fade in, held, fades out
        text_surface = self.font.render(text, True, (255, 255, 255))
        padding_x, padding_y = 16, 8
        box_rect = pygame.Rect(0, 0, text_surface.get_width() + padding_x * 2, text_surface.get_height() + padding_y * 2)
        box_rect.centerx = WINDOW_WIDTH // 2
        box_rect.y = 18

        box_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(box_surface, (20, 20, 28, min(230, alpha)), box_surface.get_rect(), border_radius=8)
        pygame.draw.rect(box_surface, (*ACCENT_GOLD, alpha), box_surface.get_rect(), width=2, border_radius=8)
        window.blit(box_surface, box_rect.topleft)
        text_surface.set_alpha(alpha)
        window.blit(text_surface, (box_rect.x + padding_x, box_rect.y + padding_y))

    def _gather_light_sources(self, world, camera):
        margin = LIGHT_SEARCH_MARGIN_TILES
        x_start = max(0, int(camera.x // TILE_SIZE) - margin)
        x_end = min(WORLD_WIDTH_TILES - 1, int((camera.x + camera.view_width) // TILE_SIZE) + margin)
        y_start = max(0, int(camera.y // TILE_SIZE) - margin)
        y_end = min(WORLD_HEIGHT_TILES - 1, int((camera.y + camera.view_height) // TILE_SIZE) + margin)
        raw_sources = lighting.find_light_sources(world, x_start, x_end, y_start, y_end)

        flicker = 1.0 + TORCH_FLICKER_AMPLITUDE * math.sin(pygame.time.get_ticks() / 1000.0 * TORCH_FLICKER_SPEED)
        return [(x, y, min(1.0, strength * flicker)) for x, y, strength in raw_sources]

    def _get_darkness_overlay(self, width: int, height: int):
        key = (width, height)
        overlay = self._darkness_overlay_cache.get(key)
        if overlay is None:
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((8, 8, 20, 255))
            self._darkness_overlay_cache[key] = overlay
        return overlay

    def _darken_sprite(self, sprite, light_level: float):
        """Darkens a sprite for lighting while respecting its own
        transparency (a plain rectangular overlay would show up as a boxy
        halo around a non-square silhouette). RGB-only multiply leaves the
        alpha channel -- and therefore the sprite's outline -- untouched."""
        if light_level >= 0.999:
            return sprite
        tint = int(255 * max(0.0, min(1.0, light_level)))
        darkened = sprite.copy()
        multiplier = pygame.Surface(sprite.get_size())
        multiplier.fill((tint, tint, tint))
        darkened.blit(multiplier, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        return darkened

    @staticmethod
    def _dim_color(color, light_level: float):
        factor = max(0.0, min(1.0, light_level))
        return tuple(int(c * factor) for c in color)

    def _draw_darkness_at(self, window, screen_x, screen_y, width, height, light_level: float) -> None:
        if light_level >= 0.999:
            return
        alpha = int((1.0 - light_level) * MAX_DARKNESS_ALPHA)
        if alpha <= 0:
            return
        overlay = self._get_darkness_overlay(width, height)
        overlay.set_alpha(alpha)
        window.blit(overlay, (int(screen_x), int(screen_y)))

    def _draw_background(self, window, camera, world_clock) -> None:
        tile = self.background_tile
        w, h = tile.get_size()
        offset_x = int((camera.x * BACKGROUND_PARALLAX) % w)
        offset_y = int((camera.y * BACKGROUND_PARALLAX) % h)
        for x in range(-offset_x, WINDOW_WIDTH, w):
            for y in range(-offset_y, WINDOW_HEIGHT, h):
                window.blit(tile, (x, y))
        self._draw_sky_tint(window, world_clock)

    def _draw_sky_tint(self, window, world_clock) -> None:
        # day_wave: 0 at midnight, 1 at noon -- reuses WorldClock's own
        # ambient curve instead of recomputing the cosine, so the two never drift.
        day_wave = (world_clock.ambient_light - NIGHT_MIN_AMBIENT) / (DAY_MAX_AMBIENT - NIGHT_MIN_AMBIENT)
        night_factor = 1.0 - day_wave
        sunset_factor = max(0.0, 1.0 - abs(day_wave - 0.5) * 2.0)  # peaks mid-transition (dawn/dusk)

        if sunset_factor > 0.01:
            self._sunset_overlay.set_alpha(int(sunset_factor * 90))
            window.blit(self._sunset_overlay, (0, 0))
        if night_factor > 0.01:
            self._night_overlay.set_alpha(int(night_factor * 150))
            window.blit(self._night_overlay, (0, 0))

    def _draw_combat_level_bar(self, window, player) -> None:
        """Always-visible top-left HUD bar (user-requested): Combat Lv
        (a flavor average of Attack/Defense/Magic/Hitpoints, see
        Skills.combat_level) plus a % progress bar toward each of those
        skills' next level, averaged (Skills.combat_level_progress_ratio)
        -- Combat Lv has no XP track of its own to show a "real" bar for,
        this is the closest honest approximation. Full per-skill detail
        lives in the Skills screen (K). Wrapped in its own translucent
        panel (same technique as _draw_notification) so the white text
        stays readable regardless of sky color or bar fill."""
        ratio = player.skills.combat_level_progress_ratio()
        label_surf = self.font.render(f"Combat Lv {player.skills.combat_level()}", True, (255, 255, 255))
        pct_surf = self.font.render(f"{int(ratio * 100)}%", True, (255, 255, 255))

        padding = 8
        content_width = max(label_surf.get_width(), COMBAT_LEVEL_BAR_WIDTH + 8 + pct_surf.get_width())
        panel_rect = pygame.Rect(16, 16, padding * 2 + content_width, padding * 2 + label_surf.get_height() + 4 + COMBAT_LEVEL_BAR_HEIGHT)

        panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (20, 20, 28, 200), panel_surface.get_rect(), border_radius=8)
        window.blit(panel_surface, panel_rect.topleft)
        pygame.draw.rect(window, ACCENT_GOLD, panel_rect, width=1, border_radius=8)

        window.blit(label_surf, (panel_rect.x + padding, panel_rect.y + padding))

        bar_rect = pygame.Rect(
            panel_rect.x + padding, panel_rect.y + padding + label_surf.get_height() + 4,
            COMBAT_LEVEL_BAR_WIDTH, COMBAT_LEVEL_BAR_HEIGHT,
        )
        pygame.draw.rect(window, HUD_BG, bar_rect, border_radius=4)
        fill_width = max(0, min(bar_rect.width, int(bar_rect.width * ratio)))
        if fill_width > 0:
            pygame.draw.rect(window, ACCENT_GOLD, (bar_rect.x, bar_rect.y, fill_width, bar_rect.height), border_radius=4)
        pygame.draw.rect(window, (0, 0, 0), bar_rect, width=1, border_radius=4)

        window.blit(pct_surf, (bar_rect.right + 8, bar_rect.centery - pct_surf.get_height() // 2))

    def _draw_day_night_indicator(self, window, world_clock) -> None:
        cx, cy, radius = WINDOW_WIDTH - 30, 30, 12
        color = (200, 205, 225) if world_clock.is_night else (255, 220, 90)
        pygame.draw.circle(window, color, (cx, cy), radius)
        pygame.draw.circle(window, (20, 20, 20), (cx, cy), radius, 1)
        text = self.font.render(f"Day {world_clock.day_count}  {world_clock.clock_string()}", True, (255, 255, 255))
        window.blit(text, (cx - radius - text.get_width() - 10, cy - text.get_height() // 2))

    def _tile_texture(self, tile_id: int, size: int):
        cache_key = (tile_id, size)
        cached = self._scaled_tile_cache.get(cache_key)
        if cached is not None:
            return cached
        base = self.tile_textures.get(tile_id)
        if base is None:
            # No art loaded for this tile id -- fall back to its TileDef
            # color so a newly-added tile is still visible before art exists.
            surface = pygame.Surface((size, size))
            surface.fill(tile_registry.get(tile_id).color)
        elif size == TILE_SIZE:
            surface = base
        else:
            surface = pygame.transform.scale(base, (size, size))
        self._scaled_tile_cache[cache_key] = surface
        return surface

    def _world_tile_texture(self, world, player, tx: int, ty: int, tile_id: int, size: int):
        """Same as _tile_texture, except the two tiles with per-instance
        dynamic visual state (a specific Falling Platform mid-crumble, or
        the one Checkpoint tile that's the player's current spawn point)
        bypass the plain id->texture cache to pick their animated frame."""
        if tile_id == CRUMBLE_PLATFORM_ID and world.crumbling_tile_pos == (tx, ty):
            frames = self.crumble_shake_frames
            frame = frames[(self._anim_counter // PLAYER_ANIMATION_FRAME_DELAY) % len(frames)]
            return frame if size == TILE_SIZE else pygame.transform.scale(frame, (size, size))
        if tile_id == CHECKPOINT_ID and tx * TILE_SIZE == int(player.spawn_x) and ty * TILE_SIZE == int(player.spawn_y):
            frames = self.checkpoint_active_frames
            frame = frames[(self._anim_counter // PLAYER_ANIMATION_FRAME_DELAY) % len(frames)]
            return frame if size == TILE_SIZE else pygame.transform.scale(frame, (size, size))
        return self._tile_texture(tile_id, size)

    def _draw_world(self, window, world, camera, light_sources, ambient_light, player) -> None:
        tile_px = int(round(TILE_SIZE * camera.zoom))
        tile_x_start = max(0, int(camera.x // TILE_SIZE))
        tile_x_end = min(WORLD_WIDTH_TILES - 1, int((camera.x + camera.view_width) // TILE_SIZE) + 1)
        tile_y_start = max(0, int(camera.y // TILE_SIZE))
        tile_y_end = min(WORLD_HEIGHT_TILES - 1, int((camera.y + camera.view_height) // TILE_SIZE) + 1)

        for tx in range(tile_x_start, tile_x_end + 1):
            surface_y = world.surface_height_at(tx)
            for ty in range(tile_y_start, tile_y_end + 1):
                tile_id = world.get_tile(tx, ty)
                if tile_id == AIR_ID:
                    continue
                texture = self._world_tile_texture(world, player, tx, ty, tile_id, tile_px)
                screen_x, screen_y = camera.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                window.blit(texture, (int(screen_x), int(screen_y)))
                local_ambient = lighting.ambient_light_for_depth(ty - surface_y, ambient_light)
                light = lighting.light_level_at(tx + 0.5, ty + 0.5, light_sources, local_ambient)
                self._draw_darkness_at(window, screen_x, screen_y, tile_px, tile_px, light)

    def _player_animation_state(self, player) -> str:
        if player.double_jump_visual_timer > 0.0:
            return "double_jump"
        if not player.on_ground:
            return "jump" if player.y_vel < 0 else "fall"
        if player.x_vel != 0:
            return "run"
        return "idle"

    def _draw_shadow_at(self, window, camera, feet_x: float, feet_y: float, width_px: float) -> None:
        """A persistent decal under a grounded character/enemy (see
        particles.py's docstring for why this isn't a spawned particle)."""
        size = max(8, int(width_px * 0.8))
        shadow = pygame.transform.scale(self.shadow_texture, (size, size // 2))
        window.blit(shadow, (feet_x - size / 2, feet_y - size / 4))

    def _draw_player(self, window, world, player, camera, light_sources, ambient_light) -> None:
        state = self._player_animation_state(player)
        direction = "right" if player.facing_right else "left"
        frames = self.character_animations[player.character_id][(state, direction)]
        frame_index = (self._anim_counter // PLAYER_ANIMATION_FRAME_DELAY) % len(frames)
        sprite = frames[frame_index]

        if camera.zoom != 1.0:
            size = (int(sprite.get_width() * camera.zoom), int(sprite.get_height() * camera.zoom))
            sprite = pygame.transform.scale(sprite, size)

        surface_y = world.surface_height_at(int(player.center_x // TILE_SIZE))
        local_ambient = lighting.ambient_light_for_depth(player.center_y / TILE_SIZE - surface_y, ambient_light)
        light = lighting.light_level_at(player.center_x / TILE_SIZE, player.center_y / TILE_SIZE, light_sources, local_ambient)
        sprite = self._darken_sprite(sprite, light)

        # The sprite is visually wider/taller than the (narrower) collision
        # box, so anchor it by feet-center rather than top-left.
        feet_x, feet_y = camera.world_to_screen(player.center_x, player.y + player.height)
        if player.on_ground:
            self._draw_shadow_at(window, camera, feet_x, feet_y, sprite.get_width())
        draw_x = feet_x - sprite.get_width() / 2
        draw_y = feet_y - sprite.get_height()
        window.blit(sprite, (draw_x, draw_y))

    def _draw_enemies(self, window, world, enemies, camera, light_sources, ambient_light) -> None:
        for enemy in enemies:
            if not enemy.alive:
                continue
            screen_x, screen_y = camera.world_to_screen(enemy.x, enemy.y)
            w = enemy.width * camera.zoom
            h = enemy.height * camera.zoom
            color = enemy.enemy_def.color
            flash = enemy.invulnerability_remaining > 0.0
            base_color = (255, 255, 255) if flash else color
            # Enemies are flat vector shapes (no texture/transparency to
            # protect), so dimming the fill color directly is simpler and
            # artifact-free compared to a rectangular overlay.
            surface_y = world.surface_height_at(int(enemy.center_x // TILE_SIZE))
            local_ambient = lighting.ambient_light_for_depth(enemy.center_y / TILE_SIZE - surface_y, ambient_light)
            light = lighting.light_level_at(enemy.center_x / TILE_SIZE, enemy.center_y / TILE_SIZE, light_sources, local_ambient)
            draw_color = self._dim_color(base_color, light)
            ai_type = enemy.enemy_def.ai_type
            if enemy.on_ground:
                self._draw_shadow_at(window, camera, screen_x + w / 2, screen_y + h, w)
            if ai_type == AIType.HOP:
                pygame.draw.ellipse(window, draw_color, (screen_x, screen_y, w, h))
            elif ai_type == AIType.FLY:
                points = [(screen_x + w / 2, screen_y), (screen_x + w, screen_y + h / 2),
                          (screen_x + w / 2, screen_y + h), (screen_x, screen_y + h / 2)]
                pygame.draw.polygon(window, draw_color, points)
            else:
                pygame.draw.rect(window, draw_color, (screen_x, screen_y, w, h))
            pygame.draw.rect(window, (20, 20, 20), (screen_x, screen_y, w, h), 1)

            self._draw_entity_health_bar(window, enemy, screen_x, screen_y, w)

    def _draw_entity_health_bar(self, window, entity, screen_x, screen_y, width) -> None:
        if entity.health >= entity.enemy_def.max_health:
            return
        ratio = max(0.0, entity.health / entity.enemy_def.max_health)
        bar_y = screen_y - 8
        pygame.draw.rect(window, HEALTH_BG, (screen_x, bar_y, width, 4))
        pygame.draw.rect(window, HEALTH_FG, (screen_x, bar_y, width * ratio, 4))

    def _draw_summons(self, window, summons, camera, light_sources, ambient_light) -> None:
        """Summons have no dedicated art (no sprites exist for them, same
        as enemies) and no health bar (they can't be damaged in this
        pass -- see game/entities/summon.py) -- just a small glowing
        flat-colored shape that follows the world's own lighting."""
        for summon in summons:
            if not summon.alive:
                continue
            screen_x, screen_y = camera.world_to_screen(summon.x, summon.y)
            w = summon.width * camera.zoom
            h = summon.height * camera.zoom
            local_ambient = lighting.ambient_light_for_depth(0.0, ambient_light)
            light = lighting.light_level_at(summon.center_x / TILE_SIZE, summon.center_y / TILE_SIZE, light_sources, local_ambient)
            draw_color = self._dim_color(summon.summon_def.color, max(light, 0.6))  # a summon reads as faintly self-lit
            pygame.draw.ellipse(window, draw_color, (screen_x, screen_y, w, h))
            pygame.draw.ellipse(window, (250, 250, 245), (screen_x, screen_y, w, h), 1)

    def _draw_projectiles(self, window, projectiles, camera) -> None:
        for projectile in projectiles:
            screen_x, screen_y = camera.world_to_screen(projectile.x, projectile.y)
            size = max(2, projectile.width * camera.zoom)
            pygame.draw.circle(window, (90, 60, 30), (int(screen_x + size / 2), int(screen_y + size / 2)), int(size / 2))

    def _draw_hook_line(self, window, player, camera) -> None:
        if player.hook_target is None:
            return
        start = camera.world_to_screen(player.center_x, player.center_y)
        end = camera.world_to_screen(*player.hook_target)
        pygame.draw.line(window, (150, 110, 60), start, end, width=max(2, int(3 * camera.zoom)))
        pygame.draw.circle(window, (90, 90, 100), (int(end[0]), int(end[1])), max(3, int(4 * camera.zoom)))

    def _draw_melee_swing(self, window, player, camera) -> None:
        if player.melee_swing_timer <= 0.0:
            return
        progress = player.melee_swing_timer / MELEE_SWING_VISUAL_DURATION_S  # 1 -> 0
        aim_dx, aim_dy = player.melee_swing_aim
        center_angle = math.atan2(-aim_dy, aim_dx)  # screen y-down -> math y-up
        half_arc = math.radians(MELEE_ARC_DEGREES / 2)

        radius = (MELEE_REACH_TILES * TILE_SIZE + player.width / 2) * camera.zoom
        screen_cx, screen_cy = camera.world_to_screen(player.center_x, player.center_y)
        rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        rect.center = (screen_cx, screen_cy)

        alpha = int(220 * progress)
        arc_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.arc(
            arc_surface, (255, 255, 255, alpha),
            pygame.Rect(0, 0, rect.width, rect.height),
            center_angle - half_arc, center_angle + half_arc,
            width=max(2, int(4 * camera.zoom)),
        )
        window.blit(arc_surface, rect.topleft)

    def _draw_aim_reticle(self, window, player) -> None:
        selected = player.inventory.get_selected_item()
        if selected is None:
            return
        item_def = item_registry.get(selected.item_id)
        if not item_def.is_weapon:
            return
        mouse_x, mouse_y = pygame.mouse.get_pos()
        color = (255, 90, 90) if item_def.is_ranged else (255, 220, 80)
        pygame.draw.circle(window, color, (mouse_x, mouse_y), 7, 2)
        pygame.draw.line(window, color, (mouse_x - 10, mouse_y), (mouse_x - 4, mouse_y), 2)
        pygame.draw.line(window, color, (mouse_x + 4, mouse_y), (mouse_x + 10, mouse_y), 2)
        pygame.draw.line(window, color, (mouse_x, mouse_y - 10), (mouse_x, mouse_y - 4), 2)
        pygame.draw.line(window, color, (mouse_x, mouse_y + 4), (mouse_x, mouse_y + 10), 2)

    def _draw_health(self, window, player) -> None:
        ratio = max(0.0, player.health / player.max_health)
        bar_rect = (16, WINDOW_HEIGHT - 40, 200, 20)
        pygame.draw.rect(window, HEALTH_BG, bar_rect)
        pygame.draw.rect(window, HEALTH_FG, (16, WINDOW_HEIGHT - 40, int(200 * ratio), 20))
        if player.is_regenerating():
            # Slow pulse so passive regen is visible without a numeric readout.
            pulse = 140 + int(90 * abs(math.sin(pygame.time.get_ticks() / 300)))
            pygame.draw.rect(window, (90, pulse, 90), bar_rect, width=2)
        else:
            pygame.draw.rect(window, (0, 0, 0), bar_rect, width=1)
        text = self.font.render(f"HP {player.health:.0f}/{player.max_health}", True, (255, 255, 255))
        window.blit(text, (20, WINDOW_HEIGHT - 38))

    def _draw_hotbar(self, window, inventory) -> None:
        slot_size = 48
        gap = 6
        total_width = HOTBAR_SLOTS * slot_size + (HOTBAR_SLOTS - 1) * gap
        start_x = (WINDOW_WIDTH - total_width) // 2
        y = WINDOW_HEIGHT - slot_size - 12

        for i in range(HOTBAR_SLOTS):
            slot = inventory.slots[i]
            x = start_x + i * (slot_size + gap)
            border_color = HUD_SELECTED_BORDER if i == inventory.selected_hotbar_index else HUD_BORDER
            pygame.draw.rect(window, HUD_BG, (x, y, slot_size, slot_size))
            pygame.draw.rect(window, border_color, (x, y, slot_size, slot_size), 2)
            if not slot.is_empty:
                self._draw_item_icon(window, slot.item_id, x + 6, y + 6, slot_size - 12)
                qty_text = self.font.render(str(slot.quantity), True, (255, 255, 255))
                window.blit(qty_text, (x + slot_size - 18, y + slot_size - 18))

    def _draw_panel_chrome(self, window, rect, title, header_height) -> None:
        """Shared panel look for inventory/crafting: rounded body, a
        distinct header bar, and a gold-accented border."""
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(overlay, PANEL_BG, overlay.get_rect(), border_radius=10)
        window.blit(overlay, rect.topleft)
        pygame.draw.rect(window, PANEL_BORDER, rect, width=2, border_radius=10)

        header_rect = pygame.Rect(rect.x, rect.y, rect.width, header_height)
        header_surface = pygame.Surface(header_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(header_surface, PANEL_HEADER_BG, header_surface.get_rect(), border_radius=10)
        pygame.draw.rect(header_surface, PANEL_HEADER_BG, (0, header_rect.height // 2, header_rect.width, header_rect.height // 2))
        window.blit(header_surface, header_rect.topleft)
        pygame.draw.line(window, ACCENT_GOLD, (rect.x, header_rect.bottom), (rect.right, header_rect.bottom), 2)

        title_surface = self.font.render(title, True, (255, 255, 255))
        window.blit(title_surface, (rect.x + 14, header_rect.centery - title_surface.get_height() // 2))

    def _draw_item_slot(self, window, rect, slot=None, item_id=None, quantity=None, empty_label=None, highlight=False) -> None:
        """Draws one bordered inventory-style slot. Accepts either an
        Inventory Slot object, or a raw (item_id, quantity) pair, so bag
        slots and equipment slots share one drawing path."""
        if slot is not None:
            item_id = None if slot.is_empty else slot.item_id
            quantity = None if slot.is_empty else slot.quantity

        bg = (48, 44, 60) if highlight else HUD_BG
        pygame.draw.rect(window, bg, rect, border_radius=6)

        if item_id is not None:
            border_color = _RARITY_BORDER_COLOR.get(item_registry.get(item_id).rarity, HUD_BORDER)
            pygame.draw.rect(window, border_color, rect, width=2, border_radius=6)
            padding = 6
            self._draw_item_icon(window, item_id, rect.x + padding, rect.y + padding, rect.width - padding * 2)
            if quantity is not None and quantity > 1:
                qty_text = self.font.render(str(quantity), True, (255, 255, 255))
                window.blit(qty_text, (rect.right - qty_text.get_width() - 3, rect.bottom - qty_text.get_height() - 2))
        else:
            pygame.draw.rect(window, HUD_BORDER, rect, width=1, border_radius=6)
            if empty_label:
                label_surface = self.font.render(empty_label, True, (110, 108, 120))
                window.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _wrap_text(self, text: str, max_width: int) -> list:
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if self.font.size(candidate)[0] <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _item_tooltip_stat_lines(self, item_def) -> list:
        """(text, color) lines for an item tooltip's stat block -- varies
        by category, since e.g. mining_power only means anything for a
        tool and defense only for armor."""
        lines = []
        if item_def.is_tool:
            lines.append((f"Mining Power: {item_def.mining_power:.0f}", (200, 220, 255)))
            if item_def.tool_type:
                lines.append((f"Tool Type: {item_def.tool_type.capitalize()}", (200, 220, 255)))
        if item_def.is_weapon:
            lines.append((f"Damage: {item_def.damage:.0f}", (255, 200, 200)))
            lines.append(("Ranged" if item_def.is_ranged else "Melee", (200, 190, 190)))
        if item_def.equip_slot is not None:
            if item_def.defense > 0:
                lines.append((f"Defense: {item_def.defense:.0f}", (200, 255, 210)))
            lines.append((f"Slot: {item_def.equip_slot.capitalize()}", (170, 165, 185)))
            if item_def.accessory_kind is not None:
                lines.append(("Press E to use", (200, 220, 255)))
        if item_def.heal_amount > 0:
            lines.append((f"Heals {item_def.heal_amount:.0f} HP", (255, 210, 210)))
        if item_def.max_durability is not None:
            lines.append((f"Durability: {item_def.max_durability}", (170, 165, 185)))
        if item_def.value > 0:
            lines.append((f"Value: {item_def.value}", (230, 200, 120)))
        return lines

    def _draw_item_tooltip(self, window, item_id: str, quantity, mouse_pos) -> None:
        """A floating tooltip near the cursor for whichever bag/equipment
        slot is currently hovered: name, category/rarity, description, and
        a category-specific stat block (see _item_tooltip_stat_lines)."""
        item_def = item_registry.get(item_id)
        rarity_color = _RARITY_BORDER_COLOR.get(item_def.rarity, HUD_BORDER)

        desc_lines = self._wrap_text(item_def.description, ITEM_TOOLTIP_WIDTH - 24)
        stat_lines = self._item_tooltip_stat_lines(item_def)

        name_surface = self.font.render(item_def.name, True, rarity_color)
        category_surface = self.font.render(
            f"{item_def.category.value.capitalize()} · {item_def.rarity.value.capitalize()}",
            True, (170, 165, 185),
        )

        content_height = 10 + name_surface.get_height() + 4 + category_surface.get_height() + 10
        content_height += len(desc_lines) * 16
        if stat_lines:
            content_height += 8 + len(stat_lines) * 16
        if quantity is not None and quantity > 1:
            content_height += 18

        width = ITEM_TOOLTIP_WIDTH
        height = content_height + 12
        x = min(mouse_pos[0] + ITEM_TOOLTIP_CURSOR_OFFSET, WINDOW_WIDTH - width - 6)
        y = min(mouse_pos[1] + ITEM_TOOLTIP_CURSOR_OFFSET, WINDOW_HEIGHT - height - 6)
        rect = pygame.Rect(x, y, width, height)

        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(overlay, PANEL_BG, overlay.get_rect(), border_radius=8)
        window.blit(overlay, rect.topleft)
        pygame.draw.rect(window, rarity_color, rect, width=2, border_radius=8)

        ty = rect.y + 10
        window.blit(name_surface, (rect.x + 12, ty))
        ty += name_surface.get_height() + 4
        window.blit(category_surface, (rect.x + 12, ty))
        ty += category_surface.get_height() + 10

        for line in desc_lines:
            line_surface = self.font.render(line, True, (215, 212, 222))
            window.blit(line_surface, (rect.x + 12, ty))
            ty += 16

        if stat_lines:
            ty += 4
            pygame.draw.line(window, PANEL_BORDER, (rect.x + 12, ty), (rect.right - 12, ty), 1)
            ty += 8
            for text, color in stat_lines:
                line_surface = self.font.render(text, True, color)
                window.blit(line_surface, (rect.x + 12, ty))
                ty += 16

        if quantity is not None and quantity > 1:
            qty_surface = self.font.render(f"Quantity: {quantity}", True, (200, 200, 210))
            window.blit(qty_surface, (rect.x + 12, ty))

    def _draw_inventory_screen(self, window, player) -> None:
        inventory = player.inventory
        panel_rect = pygame.Rect(INVENTORY_PANEL_X, INVENTORY_PANEL_Y, INVENTORY_PANEL_WIDTH, INVENTORY_PANEL_HEIGHT)
        self._draw_panel_chrome(window, panel_rect, "Character (E to close)", INVENTORY_TITLE_HEIGHT)

        divider_x = INVENTORY_PANEL_X + INVENTORY_LEFT_WIDTH
        pygame.draw.line(
            window, PANEL_BORDER,
            (divider_x, panel_rect.y + INVENTORY_TITLE_HEIGHT), (divider_x, panel_rect.bottom - 10), 2,
        )

        self._draw_equipment_column(window, player)

        mouse_pos = pygame.mouse.get_pos()
        for index, slot in enumerate(inventory.slots):
            rect = inventory_bag_slot_rect(index)
            self._draw_item_slot(window, rect, slot=slot, highlight=rect.collidepoint(mouse_pos))

        hovered_item_id, hovered_quantity = self._hovered_inventory_item(player, mouse_pos)
        if hovered_item_id is not None:
            self._draw_item_tooltip(window, hovered_item_id, hovered_quantity, mouse_pos)

    def _hovered_inventory_item(self, player, mouse_pos):
        """(item_id, quantity) for whatever bag or equipment slot the
        mouse is currently over -- quantity is None for an equipment slot
        (always exactly one equipped) or an empty/no-hit result."""
        bag_index = inventory_bag_index_at_screen_pos(mouse_pos, len(player.inventory.slots))
        if bag_index is not None:
            slot = player.inventory.slots[bag_index]
            return (None, None) if slot.is_empty else (slot.item_id, slot.quantity)

        slot_name = equipment_slot_at_screen_pos(mouse_pos)
        if slot_name is not None:
            item_id = player.equipment.get(slot_name)
            if item_id is not None:
                return item_id, None

        return None, None

    def _draw_equipment_column(self, window, player) -> None:
        portrait_size = 84
        portrait_rect = pygame.Rect(0, 0, portrait_size, portrait_size)
        portrait_rect.centerx = INVENTORY_PANEL_X + INVENTORY_LEFT_WIDTH // 2
        portrait_rect.y = INVENTORY_PANEL_Y + INVENTORY_TITLE_HEIGHT + 10
        pygame.draw.rect(window, HUD_BG, portrait_rect, border_radius=8)
        pygame.draw.rect(window, ACCENT_GOLD, portrait_rect, width=2, border_radius=8)
        idle_frame = self.character_animations[player.character_id][("idle", "right" if player.facing_right else "left")][0]
        portrait_sprite = pygame.transform.scale(idle_frame, (portrait_size - 12, portrait_size - 12))
        window.blit(portrait_sprite, (portrait_rect.x + 6, portrait_rect.y + 6))

        mouse_pos = pygame.mouse.get_pos()
        for slot_name in _EQUIPMENT_SLOT_ORDER:
            rect = equipment_slot_rect(slot_name)
            item_id = player.equipment.get(slot_name)
            self._draw_item_slot(
                window, rect, item_id=item_id, quantity=None,
                empty_label=_EQUIPMENT_SLOT_LABELS[slot_name], highlight=rect.collidepoint(mouse_pos),
            )

        stats_y = equipment_slot_rect(_EQUIPMENT_SLOT_ORDER[-1]).bottom + 16
        selected = player.inventory.get_selected_item()
        attack_text = "-"
        if selected is not None:
            selected_def = item_registry.get(selected.item_id)
            if selected_def.is_weapon:
                attack_text = f"{selected_def.damage * player.skills.attack_damage_multiplier():.0f}"
        stats_lines = [
            f"HP: {player.health:.0f}/{player.max_health}",
            f"Defense: {combat_system.player_total_defense(player):.0f}",
            f"Attack: {attack_text}",
            f"Combat Lv: {player.skills.combat_level()}",
        ]
        for i, line in enumerate(stats_lines):
            text_surface = self.font.render(line, True, (220, 220, 225))
            window.blit(text_surface, (INVENTORY_PANEL_X + 16, stats_y + i * 18))

        self._draw_skills_summary(window, player, stats_y + len(stats_lines) * 18 + 12)

    def _draw_skills_summary(self, window, player, y: int) -> None:
        """A compact 2-column skill-level grid on the character sheet
        (full detail -- xp bars, the tree -- lives in the Skills screen,
        K). Rounds the character sheet out into an actual "at a glance"
        summary instead of just the 3 combat-derived numbers above it."""
        header = self.font.render("Skills", True, (170, 150, 100))
        window.blit(header, (INVENTORY_PANEL_X + 16, y))

        col_width = (INVENTORY_LEFT_WIDTH - 16) // 2
        for index, skill_id in enumerate(SKILL_IDS):
            col, row = index % 2, index // 2
            text = f"{_SKILL_ABBREVIATIONS[skill_id]} {player.skills.level(skill_id)}"
            surf = self.font.render(text, True, (200, 200, 205))
            window.blit(surf, (INVENTORY_PANEL_X + 16 + col * col_width, y + 22 + row * 18))

    def _draw_crafting_screen(self, window, world, player, furnace_manager, scroll_y: int) -> None:
        discovered = player.discovered_item_ids
        panel_height = crafting_panel_height(discovered)
        panel_rect = pygame.Rect(CRAFTING_PANEL_X, CRAFTING_PANEL_Y, CRAFTING_PANEL_WIDTH, panel_height)
        self._draw_panel_chrome(window, panel_rect, "Crafting (C to close)", CRAFTING_TITLE_HEIGHT)

        grid_rect = pygame.Rect(
            CRAFTING_PANEL_X, CRAFTING_PANEL_Y + CRAFTING_TITLE_HEIGHT,
            CRAFTING_PANEL_PADDING + CRAFTING_GRID_WIDTH, panel_height - CRAFTING_TITLE_HEIGHT,
        )
        previous_clip = window.get_clip()
        window.set_clip(grid_rect)

        mouse_pos = pygame.mouse.get_pos()
        layout = list(_crafting_layout(scroll_y, discovered))
        hovered_recipe = None
        cell_index = 0
        for title, recipes in _recipe_sections(discovered):
            if not recipes:
                continue
            _, first_cell_rect = layout[cell_index]
            header_rect = pygame.Rect(
                CRAFTING_PANEL_X + CRAFTING_PANEL_PADDING, first_cell_rect.y - CRAFTING_SECTION_HEADER_HEIGHT,
                CRAFTING_GRID_WIDTH, CRAFTING_SECTION_HEADER_HEIGHT,
            )
            header_text = self.font.render(title.upper(), True, ACCENT_GOLD)
            window.blit(header_text, (header_rect.x, header_rect.y + 2))
            pygame.draw.line(window, PANEL_BORDER, (header_rect.x, header_rect.bottom - 2), (header_rect.x + CRAFTING_GRID_WIDTH, header_rect.bottom - 2), 1)

            for recipe in recipes:
                _, cell_rect = layout[cell_index]
                is_hovered = cell_rect.collidepoint(mouse_pos)
                if is_hovered:
                    hovered_recipe = recipe
                self._draw_recipe_cell(window, world, player, furnace_manager, recipe, cell_rect, is_hovered)
                cell_index += 1

        window.set_clip(previous_clip)
        self._draw_scrollbar(window, grid_rect, panel_rect, scroll_y, crafting_max_scroll(discovered))

        details_rect = pygame.Rect(
            grid_rect.right + CRAFTING_DIVIDER_GAP, grid_rect.y,
            CRAFTING_DETAILS_WIDTH, grid_rect.height,
        )
        pygame.draw.line(
            window, PANEL_BORDER,
            (grid_rect.right + CRAFTING_DIVIDER_GAP // 2, grid_rect.y),
            (grid_rect.right + CRAFTING_DIVIDER_GAP // 2, grid_rect.bottom - 10), 1,
        )
        self._draw_recipe_details(window, world, player, furnace_manager, hovered_recipe, details_rect)

    def _draw_scrollbar(self, window, viewport_rect, panel_rect, scroll_y: int, max_scroll: int) -> None:
        if max_scroll <= 0:
            return
        track_rect = pygame.Rect(viewport_rect.right - 8, viewport_rect.y, 4, viewport_rect.height)
        pygame.draw.rect(window, (60, 56, 70), track_rect, border_radius=2)
        thumb_height = max(24, viewport_rect.height * viewport_rect.height // (viewport_rect.height + max_scroll))
        thumb_y = viewport_rect.y + int((viewport_rect.height - thumb_height) * (scroll_y / max_scroll))
        pygame.draw.rect(window, ACCENT_GOLD, (track_rect.x, thumb_y, 4, thumb_height), border_radius=2)

    def _recipe_cell_status(self, world, player, furnace_manager, recipe):
        """Returns (status_key, accent_color) for a discovered recipe's
        grid cell -- one of "ready"/"missing"/"needs_station" for a plain
        recipe, or "smelting"/"furnace_busy" for a smelt recipe depending
        on the nearby furnace's current job (if any)."""
        if isinstance(recipe, SmeltRecipeDef):
            active_job = furnace_manager.nearby_job(world, player.center_x, player.center_y)
            if active_job is not None:
                if active_job.bar_item_id == recipe.result_item_id:
                    return "smelting", (235, 150, 60)
                return "furnace_busy", (90, 84, 100)

        has_ingredients = crafting_system.has_ingredients(recipe, player.inventory)
        near_station = recipe.station_tile_id is None or crafting_system.is_near_station(
            world, player.center_x, player.center_y, recipe.station_tile_id,
        )
        if has_ingredients and near_station:
            return "ready", (110, 220, 110)
        if not has_ingredients:
            return "missing", (100, 96, 112)
        return "needs_station", (225, 165, 90)

    def _draw_recipe_cell(self, window, world, player, furnace_manager, recipe, cell_rect, hovered: bool) -> None:
        """A compact icon-only cell (see _draw_recipe_details for the
        actual name/ingredients/station breakdown of whichever cell is
        hovered) -- lets many discovered recipes sit side by side instead
        of one tall row each."""
        status, accent_color = self._recipe_cell_status(world, player, furnace_manager, recipe)

        bg_color = (46, 44, 56) if hovered else HUD_BG
        pygame.draw.rect(window, bg_color, cell_rect, border_radius=8)
        border_color = ACCENT_GOLD if hovered else accent_color
        pygame.draw.rect(window, border_color, cell_rect, width=3 if hovered else 2, border_radius=8)

        icon_pad = 9
        icon_size = cell_rect.width - icon_pad * 2
        self._draw_item_icon(window, recipe.result_item_id, cell_rect.x + icon_pad, cell_rect.y + icon_pad, icon_size)
        if recipe.result_quantity > 1:
            qty_text = self.font.render(str(recipe.result_quantity), True, (255, 255, 255))
            window.blit(qty_text, (cell_rect.right - qty_text.get_width() - 3, cell_rect.bottom - qty_text.get_height() - 1))

        if status == "smelting":
            active_job = furnace_manager.nearby_job(world, player.center_x, player.center_y)
            progress = 1.0 - max(0.0, min(1.0, active_job.remaining_s / active_job.total_s))
            bar_rect = pygame.Rect(cell_rect.x + 3, cell_rect.bottom - 5, cell_rect.width - 6, 3)
            pygame.draw.rect(window, (30, 24, 20), bar_rect, border_radius=2)
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * progress), bar_rect.height)
            if fill_rect.width > 0:
                pygame.draw.rect(window, (235, 150, 60), fill_rect, border_radius=2)

    def _draw_recipe_details(self, window, world, player, furnace_manager, recipe, rect: pygame.Rect) -> None:
        """The fixed side panel describing whichever grid cell is
        currently hovered -- name, station, ingredients, and its live
        ready/smelting/blocked status. Empty (a placeholder hint) when
        nothing is hovered."""
        if recipe is None:
            hint = self.font.render("Hover a recipe", True, (130, 128, 142))
            window.blit(hint, (rect.x, rect.y + 4))
            hint2 = self.font.render("for details", True, (130, 128, 142))
            window.blit(hint2, (rect.x, rect.y + 22))
            return

        status, accent_color = self._recipe_cell_status(world, player, furnace_manager, recipe)

        icon_size = 48
        icon_rect = pygame.Rect(rect.x, rect.y, icon_size, icon_size)
        pygame.draw.rect(window, HUD_BG, icon_rect, border_radius=8)
        pygame.draw.rect(window, accent_color, icon_rect, width=2, border_radius=8)
        icon_pad = 7
        self._draw_item_icon(window, recipe.result_item_id, icon_rect.x + icon_pad, icon_rect.y + icon_pad, icon_size - icon_pad * 2)
        if recipe.result_quantity > 1:
            qty_text = self.font.render(f"x{recipe.result_quantity}", True, (230, 230, 235))
            window.blit(qty_text, (icon_rect.right - qty_text.get_width() - 2, icon_rect.bottom - qty_text.get_height()))

        text_x = icon_rect.right + 10
        name_text = self.font.render(recipe.name, True, (255, 255, 255))
        window.blit(name_text, (text_x, rect.y + 2))
        station_text = self.font.render(_station_label(recipe.station_tile_id), True, (170, 165, 185))
        window.blit(station_text, (text_x, rect.y + 22))

        y = icon_rect.bottom + 14
        ingredients_title = self.font.render("Ingredients", True, (170, 165, 185))
        window.blit(ingredients_title, (rect.x, y))
        y += 20

        for item_id, qty in recipe.ingredients:
            have = player.inventory.count_item(item_id)
            self._draw_item_icon(window, item_id, rect.x, y, 22)
            count_color = (150, 230, 150) if have >= qty else (235, 130, 130)
            item_name = self.font.render(item_registry.get(item_id).name, True, (220, 218, 226))
            window.blit(item_name, (rect.x + 30, y))
            count_text = self.font.render(f"{have} / {qty}", True, count_color)
            window.blit(count_text, (rect.x + 30, y + 16))
            y += 40

        y += 8
        pygame.draw.line(window, PANEL_BORDER, (rect.x, y), (rect.right, y), 1)
        y += 10

        if status == "smelting":
            active_job = furnace_manager.nearby_job(world, player.center_x, player.center_y)
            msg = self.font.render(f"Smelting: {max(0.0, active_job.remaining_s):.1f}s left", True, (230, 200, 160))
            window.blit(msg, (rect.x, y))
        elif status == "furnace_busy":
            msg = self.font.render("Furnace is busy with", True, (200, 150, 100))
            window.blit(msg, (rect.x, y))
            msg2 = self.font.render("another bar right now", True, (200, 150, 100))
            window.blit(msg2, (rect.x, y + 16))
        elif status == "needs_station":
            msg = self.font.render(f"Needs {_station_label(recipe.station_tile_id)}", True, (235, 175, 110))
            window.blit(msg, (rect.x, y))
            msg2 = self.font.render("nearby", True, (235, 175, 110))
            window.blit(msg2, (rect.x, y + 16))
        elif status == "missing":
            msg = self.font.render("Missing ingredients", True, (235, 150, 150))
            window.blit(msg, (rect.x, y))
        else:
            is_smelt = isinstance(recipe, SmeltRecipeDef)
            action_text = "Click to start smelting" if is_smelt else "Click to craft"
            msg = self.font.render(action_text, True, (150, 230, 150))
            window.blit(msg, (rect.x, y))
            if is_smelt:
                y += 18
                time_text = self.font.render(f"Takes {recipe.smelt_time_s:.0f}s", True, (195, 190, 175))
                window.blit(time_text, (rect.x, y))

    # --- Moving hazards (Saw/Rock Head/Spike Head) ---

    def _draw_hazard_features(self, window, world, camera) -> None:
        for anchor in world.iter_hazard_anchors():
            rect = anchor.current_rect(world.elapsed_s)
            if anchor.kind == hazard_feature.SAW:
                self._draw_saw_chain(window, camera, anchor, rect)
            self._draw_hazard_sprite(window, camera, world, anchor, rect)

    def _draw_saw_chain(self, window, camera, anchor, rect) -> None:
        """A short vertical chain from the saw's ceiling mount down to its
        current position, drawn as repeated Chain.png links -- decorative,
        not part of collision."""
        link = self.hazard_textures["saw_chain_link"][0]
        link_world_size = TILE_SIZE * 0.3
        y = anchor.anchor_y - TILE_SIZE
        while y < rect.centery:
            screen_x, screen_y = camera.world_to_screen(anchor.anchor_x - link_world_size / 2, y)
            size = max(2, int(link_world_size * camera.zoom))
            window.blit(pygame.transform.scale(link, (size, size)), (screen_x, screen_y))
            y += link_world_size

    def _draw_hazard_sprite(self, window, camera, world, anchor, rect) -> None:
        screen_x, screen_y = camera.world_to_screen(rect.x, rect.y)
        draw_w = max(2, int(rect.width * camera.zoom))
        draw_h = max(2, int(rect.height * camera.zoom))
        frames = self.hazard_textures[anchor.kind]
        if anchor.kind == hazard_feature.SAW:
            frame = frames[self._anim_counter % len(frames)]
        else:
            # Rock Head/Spike Head frame lists end with one "impact" frame
            # (see assets.load_hazard_textures) shown near the extremes of
            # the swing; every frame before that is the idle blink loop.
            idle_frames, hit_frame = frames[:-1], frames[-1]
            progress = anchor.oscillation_progress(world.elapsed_s)
            if abs(progress) > 0.85:
                frame = hit_frame
            else:
                frame = idle_frames[(self._anim_counter // PLAYER_ANIMATION_FRAME_DELAY) % len(idle_frames)]
        sprite = pygame.transform.scale(frame, (draw_w, draw_h))
        window.blit(sprite, (screen_x, screen_y))

    # --- Particles (Dust, Confetti -- see particles.py) ---

    def _draw_particles(self, window, particles, camera) -> None:
        for p in particles.particles:
            frames = self.particle_textures[p.kind]
            frame = frames[p.frame_index] if p.kind == CONFETTI else frames[0]
            ratio = max(0.0, min(1.0, p.lifetime / p.max_lifetime))
            base_size = TILE_SIZE * (0.35 if p.kind == DUST else 0.3)
            size = max(2, int(base_size * camera.zoom * (ratio if p.kind == DUST else 1.0)))
            sprite = pygame.transform.scale(frame, (size, size))
            if p.kind == DUST:
                sprite.set_alpha(int(255 * ratio))
            screen_x, screen_y = camera.world_to_screen(p.x, p.y)
            window.blit(sprite, (screen_x - size / 2, screen_y - size / 2))

    # --- Skills screen (K) ---

    def _draw_skills_screen(self, window, player, selected_skill_id: str) -> None:
        panel_rect = pygame.Rect(SKILLS_PANEL_X, SKILLS_PANEL_Y, SKILLS_PANEL_WIDTH, SKILLS_PANEL_HEIGHT)
        self._draw_panel_chrome(window, panel_rect, "Skills (K to close)", SKILLS_TITLE_HEIGHT)

        skills = player.skills
        mouse_pos = pygame.mouse.get_pos()
        for index, skill_id in enumerate(SKILL_IDS):
            rect = skill_row_rect(index)
            selected = skill_id == selected_skill_id
            pygame.draw.rect(window, HUD_BG, rect, border_radius=6)
            border_color = ACCENT_GOLD if selected else (HUD_SELECTED_BORDER if rect.collidepoint(mouse_pos) else HUD_BORDER)
            pygame.draw.rect(window, border_color, rect, width=2 if selected else 1, border_radius=6)

            level = skills.level(skill_id)
            name_text = self.font.render(f"{SKILL_NAMES[skill_id]}  Lv {level}", True, (230, 230, 235))
            window.blit(name_text, (rect.x + 8, rect.y + 4))

            bar_rect = pygame.Rect(rect.x + 8, rect.bottom - 14, rect.width - 16, 6)
            pygame.draw.rect(window, HEALTH_BG, bar_rect)
            ratio = skills.level_progress_ratio(skill_id)
            pygame.draw.rect(window, (90, 170, 220), (bar_rect.x, bar_rect.y, int(bar_rect.width * ratio), bar_rect.height))
            pygame.draw.rect(window, (0, 0, 0), bar_rect, width=1)

        combat_lv_text = self.font.render(f"Combat Lv {skills.combat_level()}", True, (215, 180, 90))
        window.blit(combat_lv_text, (SKILLS_PANEL_X + 14, panel_rect.bottom - 24))

        self._draw_skill_node_panel(window, skills, selected_skill_id, mouse_pos)

    def _draw_skill_node_panel(self, window, skills, selected_skill_id: str, mouse_pos) -> None:
        details_x = SKILLS_PANEL_X + SKILLS_LIST_WIDTH + 40
        header = self.font.render(f"{SKILL_NAMES[selected_skill_id]} tree", True, (255, 255, 255))
        window.blit(header, (details_x, SKILLS_PANEL_Y + SKILLS_TITLE_HEIGHT + 14))

        if selected_skill_id == "hitpoints":
            info_lines = self._wrap_text(
                "Hitpoints has no tree of its own -- it gains XP passively "
                "from combat (Attack/Defense/Magic) and raises your max HP.",
                SKILLS_PANEL_WIDTH - SKILLS_LIST_WIDTH - 60,
            )
            for i, line in enumerate(info_lines):
                line_surf = self.font.render(line, True, (190, 190, 198))
                window.blit(line_surf, (details_x, SKILLS_PANEL_Y + SKILLS_TITLE_HEIGHT + 44 + i * 18))
            return

        points_text = self.font.render(f"Points available: {skills.available_points(selected_skill_id)}", True, (210, 190, 140))
        window.blit(points_text, (details_x, SKILLS_PANEL_Y + SKILLS_TITLE_HEIGHT + 38))

        level = skills.level(selected_skill_id)
        nodes = skill_tree_registry.nodes_for_skill(selected_skill_id)

        # Connecting lines first (a chain, tier 1 -> 2 -> 3), so node boxes
        # draw on top of the line ends rather than the line crossing them.
        for index in range(len(nodes) - 1):
            top_rect = skill_node_rect(index)
            bottom_rect = skill_node_rect(index + 1)
            unlocked_through = skills.has_node(nodes[index].id)
            line_color = ACCENT_GOLD if unlocked_through else HUD_BORDER
            pygame.draw.line(
                window, line_color,
                (top_rect.centerx, top_rect.bottom), (bottom_rect.centerx, bottom_rect.top),
                width=3 if unlocked_through else 2,
            )

        for index, node in enumerate(nodes):
            rect = skill_node_rect(index)
            unlocked = skills.has_node(node.id)
            prereq_met = node.requires_node_id is None or skills.has_node(node.requires_node_id)
            unlockable = not unlocked and prereq_met and level >= node.required_level and skills.available_points(selected_skill_id) > 0
            if unlocked:
                border_color = ACCENT_GOLD
            elif unlockable:
                border_color = (90, 200, 110)
            else:
                border_color = HUD_BORDER
            pygame.draw.rect(window, HUD_BG, rect, border_radius=8)
            pygame.draw.rect(window, border_color, rect, width=3 if (unlocked or unlockable) else 1, border_radius=8)
            # A small circular "node" marker on the connecting line, colored
            # like the box border -- reinforces the tree/chain read.
            pygame.draw.circle(window, border_color, (rect.centerx, rect.top), 5)

            name_surf = self.font.render(node.name, True, (230, 230, 235))
            window.blit(name_surf, (rect.x + 10, rect.y + 8))
            if unlocked:
                status, status_color = "Unlocked", (140, 220, 150)
            elif not prereq_met:
                status, status_color = f"Requires {skill_tree_registry.get(node.requires_node_id).name} first", (200, 130, 130)
            else:
                status, status_color = f"Requires Lv {node.required_level}", (170, 170, 180)
            status_surf = self.font.render(status, True, status_color)
            window.blit(status_surf, (rect.x + 10, rect.y + 27))
            desc_lines = self._wrap_text(node.description, rect.width - 20)
            for i, line in enumerate(desc_lines):
                line_surf = self.font.render(line, True, (200, 200, 205))
                window.blit(line_surf, (rect.x + 10, rect.y + 52 + i * 16))

    # --- Character select screen ---

    def _draw_character_select_screen(self, window, player) -> None:
        window.fill((18, 18, 24))
        title = self.big_font.render("Choose your character", True, (255, 255, 255))
        window.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 140)))

        for index, character in enumerate(character_registry.all_characters()):
            rect = character_portrait_rect(index)
            selected = character.id == player.character_id
            pygame.draw.rect(window, HUD_BG, rect, border_radius=8)
            border_color = ACCENT_GOLD if selected else HUD_BORDER
            pygame.draw.rect(window, border_color, rect, width=3 if selected else 1, border_radius=8)

            idle_frames = self.character_animations[character.id][("idle", "right")]
            frame_index = (self._anim_counter // PLAYER_ANIMATION_FRAME_DELAY) % len(idle_frames)
            sprite = pygame.transform.scale(idle_frames[frame_index], (rect.width - 20, rect.width - 20))
            window.blit(sprite, (rect.x + 10, rect.y + 6))

            name_text = self.font.render(character.name, True, (230, 230, 235))
            window.blit(name_text, name_text.get_rect(center=(rect.centerx, rect.bottom + 16)))

        hint = self.font.render("Click a character, or press Enter to confirm", True, (170, 170, 180))
        window.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 150)))

    def _draw_class_select_screen(self, window, player) -> None:
        window.fill((18, 18, 24))
        title = self.big_font.render("Choose your class", True, (255, 255, 255))
        window.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 160)))

        for index, class_def in enumerate(class_registry.all_classes()):
            rect = class_card_rect(index)
            selected = class_def.id == player.class_id
            pygame.draw.rect(window, HUD_BG, rect, border_radius=8)
            border_color = ACCENT_GOLD if selected else HUD_BORDER
            pygame.draw.rect(window, border_color, rect, width=3 if selected else 1, border_radius=8)

            name_text = self.font.render(class_def.name, True, (230, 230, 235))
            window.blit(name_text, name_text.get_rect(center=(rect.centerx, rect.top + 24)))

            desc_lines = self._wrap_text(class_def.description, rect.width - 24)
            for line_index, line in enumerate(desc_lines):
                line_surf = self.font.render(line, True, (190, 190, 198))
                window.blit(line_surf, line_surf.get_rect(center=(rect.centerx, rect.top + 60 + line_index * 18)))

        hint = self.font.render("Click a class, or press Enter to confirm", True, (170, 170, 180))
        window.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 150)))

    # --- Pause menu ---

    def _draw_pause_overlay(self, window, settings_open: bool = False) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        window.blit(overlay, (0, 0))
        title = "SETTINGS" if settings_open else "PAUSED"
        text = self.big_font.render(title, True, (255, 255, 255))
        window.blit(text, text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))

        mouse_pos = pygame.mouse.get_pos()
        labels = (
            {"zoom_out": "Zoom -", "zoom_in": "Zoom +", "back": "Back"}
            if settings_open else
            {"play": "Resume", "settings": "Settings", "save": "Save", "load": "Load", "restart": "Restart", "close": "Quit"}
        )
        for action, rect in pause_menu_button_rects(settings_open).items():
            hovered = rect.collidepoint(mouse_pos)
            pygame.draw.rect(window, (48, 44, 60) if hovered else HUD_BG, rect, border_radius=8)
            pygame.draw.rect(window, ACCENT_GOLD if hovered else HUD_BORDER, rect, width=2, border_radius=8)
            icon = self.menu_button_icons.get(action)
            if icon is not None:
                icon_size = rect.width - 20
                scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
                window.blit(scaled_icon, scaled_icon.get_rect(center=(rect.centerx, rect.centery - 8)))
            label_text = self.font.render(labels[action], True, (220, 220, 225))
            window.blit(label_text, label_text.get_rect(center=(rect.centerx, rect.bottom + 12)))

    def _draw_item_icon(self, window, item_id: str, x: int, y: int, size: int) -> None:
        item_def = item_registry.get(item_id)
        tile_icon_id = item_def.places_tile_id if item_def.places_tile_id is not None else item_def.icon_tile_id
        if tile_icon_id is not None:
            icon = self._tile_texture(tile_icon_id, size)
            window.blit(icon, (x, y))
            return
        static_icon = self.item_icons.get(item_def.icon_key)
        if static_icon is not None:
            window.blit(pygame.transform.scale(static_icon, (size, size)), (x, y))
            return
        color = _CATEGORY_SWATCH_COLOR.get(item_def.category, _DEFAULT_SWATCH_COLOR)
        pygame.draw.rect(window, color, (x, y, size, size))
