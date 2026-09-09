"""Translates raw pygame input into game actions.

Kept separate from Player/World/Renderer so input remapping later (see
README "Controles") only touches this file.
"""
import pygame

from game.settings import TILE_SIZE, PLAYER_PLACE_COOLDOWN_S
from game.items import item_registry
from game.crafting import crafting_system
from game.crafting.smelt_recipe import SmeltRecipeDef
from game.combat import combat_system
from game.combat.projectile import Projectile
from game.entities import character_registry, class_registry
from game.entities.summon import Summon
from game.skills.skills import SKILL_IDS
from game.skills.skill_tree_registry import nodes_for_skill
from game.rendering.renderer import (
    recipe_at_screen_pos, equipment_slot_at_screen_pos, inventory_bag_index_at_screen_pos,
    crafting_max_scroll, CRAFTING_SCROLL_STEP,
    character_index_at_screen_pos, class_index_at_screen_pos, pause_button_at_screen_pos,
    skill_index_at_screen_pos, skill_node_at_screen_pos,
)


class InputHandler:
    def __init__(self):
        self._place_cooldown = 0.0

    def handle_discrete_events(self, events, game_app) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                game_app.running = False
            elif game_app.character_select_open:
                self._handle_character_select_event(event, game_app)
            elif game_app.class_select_open:
                self._handle_class_select_event(event, game_app)
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event, game_app)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_app.paused:
                self._handle_pause_click(event.pos, game_app)
            elif event.type == pygame.MOUSEWHEEL and game_app.crafting_open:
                max_scroll = crafting_max_scroll(game_app.player.discovered_item_ids)
                game_app.crafting_scroll_y = max(0, min(max_scroll, game_app.crafting_scroll_y - event.y * CRAFTING_SCROLL_STEP))
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    game_app.camera.zoom_in()
                elif event.y < 0:
                    game_app.camera.zoom_out()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_app.crafting_open:
                self._handle_crafting_click(event.pos, game_app)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_app.inventory_open:
                self._handle_inventory_click(event.pos, game_app)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and game_app.inventory_open:
                self._handle_inventory_right_click(event.pos, game_app)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_app.skills_open:
                self._handle_skills_click(event.pos, game_app)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not game_app.crafting_open and not game_app.inventory_open and not game_app.skills_open:
                self._handle_attack_click(event.pos, game_app)

    def _handle_character_select_event(self, event, game_app) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = character_index_at_screen_pos(event.pos)
            if index is not None:
                game_app.player.character_id = character_registry.all_characters()[index].id
        elif event.type == pygame.KEYDOWN:
            characters = character_registry.all_characters()
            current_index = next(i for i, c in enumerate(characters) if c.id == game_app.player.character_id)
            if event.key in (pygame.K_LEFT, pygame.K_a):
                game_app.player.character_id = characters[(current_index - 1) % len(characters)].id
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                game_app.player.character_id = characters[(current_index + 1) % len(characters)].id
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                game_app.character_select_open = False
                game_app.class_select_open = True

    def _handle_class_select_event(self, event, game_app) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = class_index_at_screen_pos(event.pos)
            if index is not None:
                game_app.player.class_id = class_registry.all_classes()[index].id
        elif event.type == pygame.KEYDOWN:
            classes = class_registry.all_classes()
            current_index = next(i for i, c in enumerate(classes) if c.id == game_app.player.class_id)
            if event.key in (pygame.K_LEFT, pygame.K_a):
                game_app.player.class_id = classes[(current_index - 1) % len(classes)].id
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                game_app.player.class_id = classes[(current_index + 1) % len(classes)].id
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                game_app.class_select_open = False
                game_app.grant_class_starting_item()

    def _handle_pause_click(self, pos, game_app) -> None:
        action = pause_button_at_screen_pos(pos, game_app.settings_open)
        if action is None:
            return
        if game_app.settings_open:
            if action == "zoom_in":
                game_app.camera.zoom_in()
            elif action == "zoom_out":
                game_app.camera.zoom_out()
            elif action == "back":
                game_app.settings_open = False
        else:
            if action == "play":
                game_app.paused = False
            elif action == "settings":
                game_app.settings_open = True
            elif action == "save":
                game_app.save_game()
            elif action == "load":
                game_app.load_game()
            elif action == "restart":
                game_app.restart()
            elif action == "close":
                game_app.running = False

    def _handle_crafting_click(self, pos, game_app) -> None:
        player = game_app.player
        recipe = recipe_at_screen_pos(pos, game_app.crafting_scroll_y, player.discovered_item_ids)
        if recipe is None:
            return  # undiscovered recipes never appear in the grid, so a hit here is always discovered

        if isinstance(recipe, SmeltRecipeDef):
            game_app.furnace_manager.start_smelt(recipe, player.inventory, game_app.world, player.center_x, player.center_y)
            return

        success, newly_discovered = crafting_system.craft_and_discover(recipe, player, game_app.world)
        if success:
            for unlocked in newly_discovered:
                game_app.notifications.push(f"New recipe unlocked: {unlocked.name}")

    def _handle_inventory_click(self, pos, game_app) -> None:
        player = game_app.player

        slot_name = equipment_slot_at_screen_pos(pos)
        if slot_name is not None:
            player.equipment.unequip_to_inventory(player.inventory, slot_name)
            return

        bag_index = inventory_bag_index_at_screen_pos(pos, len(player.inventory.slots))
        if bag_index is not None:
            slot = player.inventory.slots[bag_index]
            if not slot.is_empty and item_registry.get(slot.item_id).equip_slot is not None:
                player.equipment.equip_from_inventory(player.inventory, slot.item_id)

    def _handle_inventory_right_click(self, pos, game_app) -> None:
        """Right-clicking a bag item is a quick-action shortcut: equip it
        if it's armor, otherwise send it to whichever hotbar slot is
        currently selected (swapping places with whatever's there) --
        equipment slots aren't a target for this (unequip already has its
        own left-click action)."""
        player = game_app.player
        bag_index = inventory_bag_index_at_screen_pos(pos, len(player.inventory.slots))
        if bag_index is None:
            return
        slot = player.inventory.slots[bag_index]
        if slot.is_empty:
            return
        if item_registry.get(slot.item_id).equip_slot is not None:
            player.equipment.equip_from_inventory(player.inventory, slot.item_id)
            return
        player.inventory.swap_slots(bag_index, player.inventory.selected_hotbar_index)

    def _handle_skills_click(self, pos, game_app) -> None:
        skill_index = skill_index_at_screen_pos(pos)
        if skill_index is not None:
            game_app.selected_skill_id = SKILL_IDS[skill_index]
            return

        node_index = skill_node_at_screen_pos(pos)
        if node_index is None:
            return
        nodes = nodes_for_skill(game_app.selected_skill_id)
        if node_index >= len(nodes):
            return
        game_app.player.skills.try_unlock_node(nodes[node_index].id)

    def _handle_use_accessory(self, game_app) -> None:
        if game_app.paused:
            return
        aim_world_pos = game_app.camera.screen_to_world(*pygame.mouse.get_pos())
        game_app.player.try_use_accessory(game_app.world, aim_world_pos)

    def _handle_attack_click(self, pos, game_app) -> None:
        if game_app.paused:
            return
        player = game_app.player
        blocked_reason = player.blocked_weapon_class_reason()
        if blocked_reason is not None:
            game_app.notifications.push_throttled(blocked_reason)
            return
        aim_world_pos = game_app.camera.screen_to_world(*pos)
        result = combat_system.try_attack(player, game_app.world, game_app.enemies, aim_world_pos)
        if isinstance(result, Projectile):
            game_app.projectiles.append(result)
        elif isinstance(result, Summon):
            game_app.summons = [result]

    def _handle_keydown(self, event, game_app) -> None:
        key = event.key
        if key == pygame.K_ESCAPE:
            if game_app.settings_open:
                game_app.settings_open = False
            else:
                game_app.paused = not game_app.paused
        elif key == pygame.K_i:
            game_app.inventory_open = not game_app.inventory_open
            game_app.crafting_open = False
            game_app.skills_open = False
        elif key == pygame.K_e:
            self._handle_use_accessory(game_app)
        elif key == pygame.K_c:
            game_app.crafting_open = not game_app.crafting_open
            game_app.inventory_open = False
            game_app.skills_open = False
            game_app.crafting_scroll_y = 0
        elif key == pygame.K_k:
            game_app.skills_open = not game_app.skills_open
            game_app.inventory_open = False
            game_app.crafting_open = False
        elif key == pygame.K_F3:
            game_app.debug_overlay.toggle()
        elif key == pygame.K_SPACE:
            game_app.player.jump()
        elif key == pygame.K_f:
            game_app.player.eat_selected()
        elif pygame.K_1 <= key <= pygame.K_9:
            game_app.player.inventory.select_hotbar(key - pygame.K_1)
        elif key == pygame.K_EQUALS or key == pygame.K_PLUS:
            game_app.camera.zoom_in()
        elif key == pygame.K_MINUS:
            game_app.camera.zoom_out()

    def update_continuous(self, dt: float, game_app) -> None:
        if game_app.paused:
            return

        player = game_app.player
        if not player.is_invulnerable():  # don't cancel knockback the instant it's applied
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                player.move_left()
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                player.move_right()
            else:
                player.stop_horizontal()

        if game_app.inventory_open or game_app.crafting_open or game_app.skills_open:
            return  # freeze mining/placing while browsing a menu

        mouse_buttons = pygame.mouse.get_pressed(num_buttons=3)
        mouse_pos = pygame.mouse.get_pos()
        world_x, world_y = game_app.camera.screen_to_world(*mouse_pos)
        tile_x, tile_y = int(world_x // TILE_SIZE), int(world_y // TILE_SIZE)

        self._place_cooldown = max(0.0, self._place_cooldown - dt)

        selected = player.inventory.get_selected_item()
        selected_is_weapon = selected is not None and item_registry.get(selected.item_id).is_weapon
        if selected_is_weapon:
            # Pre-aim: face the mouse continuously while a weapon is out,
            # so the swing/shot direction is never a surprise when you click.
            player.facing_right = world_x >= player.center_x

        if mouse_buttons[0] and not selected_is_weapon:
            blocked_reason = player.blocked_mining_reason(game_app.world, tile_x, tile_y)
            if blocked_reason is not None:
                game_app.notifications.push_throttled(blocked_reason)
            drop_item_id = player.try_mine(game_app.world, tile_x, tile_y, dt)
            if drop_item_id is not None:
                newly_discovered = crafting_system.collect_and_discover(player, drop_item_id, 1)
                for unlocked in newly_discovered:
                    game_app.notifications.push(f"New recipe unlocked: {unlocked.name}")
        else:
            player.cancel_mining()

        if mouse_buttons[2] and self._place_cooldown <= 0.0:
            selected = player.inventory.get_selected_item()
            if selected is not None:
                item_def = item_registry.get(selected.item_id)
                if item_def.places_tile_id is not None:
                    placed = game_app.world.try_place_tile(tile_x, tile_y, item_def.places_tile_id)
                    if placed:
                        player.inventory.remove_from_selected(1)
                        self._place_cooldown = PLAYER_PLACE_COOLDOWN_S
