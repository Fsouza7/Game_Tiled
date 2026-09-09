"""Save/load: seed, player state, world clock, in-progress furnace jobs,
and modified chunks only -- diffed against the procedural baseline, not
saved whole (see `_chunk_diff`). No NPCs to persist yet (none exist).

Single save slot (`SAVE_FILE_PATH`), matching this project's consistently
minimal scope elsewhere (one world per run, no save-file picker UI). Not
persisted: enemies, projectiles, particles, notifications -- all
transient/regenerable, same as after Restart already discards them.

`serialize`/`deserialize` are pure (no file I/O) so they're testable on
their own; `save_to_file`/`load_from_file` are thin wrappers around them.
"""
import json
import os
from typing import Optional, Tuple

from game.settings import SAVE_FILE_PATH, CHUNK_WIDTH, WORLD_WIDTH_TILES
from game.crafting.furnace_system import FurnaceManager, FurnaceJob
from game.entities import character_registry, class_registry
from game.entities.player import Player
from game.inventory.inventory import Slot
from game.skills.skills import SKILL_IDS
from game.core.world_clock import WorldClock
from game.world.world import World
from game.world.world_generator import generate_column

SAVE_FORMAT_VERSION = 1


def _chunk_diff(world: World, chunk_x: int, chunk) -> list:
    """(local_x, y, tile_id) triples for every tile in this chunk that
    differs from the procedural baseline -- generate_column is a cheap
    pure function of (seed, x), so recomputing it at save time to diff
    against is fine, the same cost already paid every chunk load/unload."""
    diff = []
    base_x = chunk_x * CHUNK_WIDTH
    for local_x in range(CHUNK_WIDTH):
        world_x = base_x + local_x
        if world_x >= WORLD_WIDTH_TILES:
            break
        baseline = generate_column(world.seed, world_x)
        live = chunk.tiles[local_x]
        for y, tile_id in enumerate(live):
            if tile_id != baseline[y]:
                diff.append((local_x, y, tile_id))
    return diff


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
            {"chunk_x": chunk_x, "diff": _chunk_diff(world, chunk_x, chunk)}
            for chunk_x, chunk in world.chunks.items() if chunk.dirty
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
