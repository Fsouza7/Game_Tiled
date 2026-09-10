"""Save/load: seed, player state (including personal-chest stash and any
in-progress timed craft -- see crafting_system.CraftJob), world
clock, in-progress furnace jobs, modified chunks, any world-generated loot
Chests that have actually been opened (see game/world/loot_chest.py) --
only those, since an untouched one re-derives its roll deterministically
from (seed, position) on first open, nothing to save ahead of time -- and
the Map screen's fog-of-war (`World.explored_cells`, see
game/world/exploration.py). Chunks are diffed against the procedural
baseline, not saved whole (see `World.chunk_diff`) -- covering both
currently-loaded dirty chunks and ones already unloaded since their last
edit (`World._unloaded_chunk_diffs`), so a chunk's edits survive the
player simply wandering far enough away before the next save. NPCs are
not persisted: they're regenerated from spawn conditions + house
assignment on load (see game/npcs/npc_spawner.py), same
transient/regenerable treatment as enemies.

Single save slot (`SAVE_FILE_PATH`), matching this project's consistently
minimal scope elsewhere (one world per run, no save-file picker UI). Not
persisted: enemies, NPCs, projectiles, particles, notifications -- all
transient/regenerable, same as after Restart already discards them.

`serialize`/`deserialize` are pure (no file I/O) so they're testable on
their own; `save_to_file`/`load_from_file` are thin wrappers around them.
"""
import json
import os
from typing import Optional, Tuple

from game.settings import SAVE_FILE_PATH, LOOT_CHEST_SLOTS
from game.crafting.furnace_system import FurnaceManager, FurnaceJob
from game.crafting.crafting_system import CraftJob
from game.entities import character_registry, class_registry
from game.entities.player import Player
from game.inventory.inventory import Inventory, Slot
from game.skills.skills import SKILL_IDS
from game.core.world_clock import WorldClock
from game.world.world import World

SAVE_FORMAT_VERSION = 1


def serialize(world: World, player: Player, world_clock: WorldClock, furnace_manager: FurnaceManager) -> dict:
    return {
        "version": SAVE_FORMAT_VERSION,
        "seed": world.seed,
        "elapsed_s": world.elapsed_s,
        "world_clock": {
            "time_of_day": world_clock.time_of_day,
            "day_count": world_clock.day_count,
        },
        "player": {
            "x": player.x, "y": player.y,
            "spawn_x": player.spawn_x, "spawn_y": player.spawn_y,
            "character_id": player.character_id,
            "class_id": player.class_id,
            "health": player.health, "max_health": player.max_health,
            "inventory": {
                "slots": [{"item_id": s.item_id, "quantity": s.quantity} for s in player.inventory.slots],
                "selected_hotbar_index": player.inventory.selected_hotbar_index,
            },
            "equipment": dict(player.equipment.slots),
            "discovered_item_ids": sorted(player.discovered_item_ids),
            "skills": {
                skill_id: {
                    "xp": player.skills.xp(skill_id),
                    "unlocked_node_ids": sorted(player.skills.unlocked_node_ids(skill_id)),
                }
                for skill_id in SKILL_IDS
            },
            "personal_chest": [
                {"item_id": s.item_id, "quantity": s.quantity} for s in player.personal_chest.slots
            ],
            "craft_job": None if player.craft_job is None else {
                "recipe_id": player.craft_job.recipe_id,
                "remaining_s": player.craft_job.remaining_s,
                "total_s": player.craft_job.total_s,
            },
        },
        "furnace_jobs": [
            {
                "x": pos[0], "y": pos[1],
                "bar_item_id": job.bar_item_id, "quantity": job.quantity,
                "remaining_s": job.remaining_s, "total_s": job.total_s,
            }
            for pos, job in furnace_manager.jobs.items()
        ],
        "dirty_chunks": [
            {"chunk_x": chunk_x, "diff": world.chunk_diff(chunk_x, chunk)}
            for chunk_x, chunk in world.chunks.items() if chunk.dirty
        ] + [
            # Chunks that were dirty but have since been unloaded (see
            # World._unloaded_chunk_diffs) -- already diffed at unload
            # time, so no need to recompute here.
            {"chunk_x": chunk_x, "diff": diff}
            for chunk_x, diff in world._unloaded_chunk_diffs.items()
        ],
        "chest_loot": [
            {
                "x": pos[0], "y": pos[1],
                "slots": [{"item_id": s.item_id, "quantity": s.quantity} for s in inventory.slots],
            }
            for pos, inventory in world.chest_loot.items()
        ],
        "explored_cells": [
            {"x": cell[0], "y": cell[1], "color": list(color)}
            for cell, color in world.explored_cells.items()
        ],
    }


def deserialize(data: dict) -> Tuple[World, Player, WorldClock, FurnaceManager]:
    world = World(data["seed"])
    world.elapsed_s = data["elapsed_s"]
    for chunk_data in data["dirty_chunks"]:
        chunk = world.get_or_create_chunk(chunk_data["chunk_x"])
        for local_x, y, tile_id in chunk_data["diff"]:
            chunk.tiles[local_x][y] = tile_id
        chunk.dirty = True
    for chest_data in data.get("chest_loot", []):
        inventory = Inventory(size=LOOT_CHEST_SLOTS)
        for index, saved_slot in enumerate(chest_data["slots"]):
            if index >= len(inventory.slots):
                break
            inventory.slots[index] = Slot(item_id=saved_slot["item_id"], quantity=saved_slot["quantity"])
        world.chest_loot[(chest_data["x"], chest_data["y"])] = inventory
    for cell_data in data.get("explored_cells", []):
        world.explored_cells[(cell_data["x"], cell_data["y"])] = tuple(cell_data["color"])

    world_clock = WorldClock()
    world_clock.time_of_day = data["world_clock"]["time_of_day"]
    world_clock.day_count = data["world_clock"]["day_count"]

    pdata = data["player"]
    character_id = pdata.get("character_id", character_registry.DEFAULT_CHARACTER_ID)
    class_id = pdata.get("class_id", class_registry.DEFAULT_CLASS_ID)
    player = Player(pdata["x"], pdata["y"], character_id, class_id)
    player.x = pdata["x"]
    player.y = pdata["y"]
    player.spawn_x = pdata["spawn_x"]
    player.spawn_y = pdata["spawn_y"]
    player.health = pdata["health"]
    player.max_health = pdata["max_health"]
    player.inventory.slots = [Slot(item_id=s["item_id"], quantity=s["quantity"]) for s in pdata["inventory"]["slots"]]
    player.inventory.selected_hotbar_index = pdata["inventory"]["selected_hotbar_index"]
    # update(), not a wholesale replace, so an old save missing a newer
    # slot (e.g. "accessory", added after this save was written) leaves
    # that slot at the constructor's default (None) instead of vanishing
    # from the dict entirely.
    player.equipment.slots.update(pdata["equipment"])
    player.discovered_item_ids = set(pdata["discovered_item_ids"])
    for skill_id, skill_data in pdata.get("skills", {}).items():
        player.skills.restore_state(skill_id, skill_data["xp"], set(skill_data["unlocked_node_ids"]))
    for index, saved_slot in enumerate(pdata.get("personal_chest", [])):
        if index >= len(player.personal_chest.slots):
            break
        player.personal_chest.slots[index] = Slot(
            item_id=saved_slot["item_id"], quantity=saved_slot["quantity"],
        )
    craft_job_data = pdata.get("craft_job")
    if craft_job_data is not None:
        player.craft_job = CraftJob(
            recipe_id=craft_job_data["recipe_id"],
            remaining_s=craft_job_data["remaining_s"],
            total_s=craft_job_data["total_s"],
        )

    furnace_manager = FurnaceManager()
    for j in data["furnace_jobs"]:
        furnace_manager.jobs[(j["x"], j["y"])] = FurnaceJob(
            bar_item_id=j["bar_item_id"], quantity=j["quantity"],
            remaining_s=j["remaining_s"], total_s=j["total_s"],
        )

    return world, player, world_clock, furnace_manager


def save_to_file(world: World, player: Player, world_clock: WorldClock, furnace_manager: FurnaceManager, path: str = SAVE_FILE_PATH) -> None:
    data = serialize(world, player, world_clock, furnace_manager)
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def load_from_file(path: str = SAVE_FILE_PATH) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save_exists(path: str = SAVE_FILE_PATH) -> bool:
    return os.path.exists(path)
