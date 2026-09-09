"""Runtime NPC instance: an NpcDef plus a world position.

NPCs don't walk, fall, or fight -- they stand at a home position chosen
at spawn time (a House interior, or a surface fallback near spawn). That's
a deliberate simplification: there's no pathfinding/schedule system, and
a floating NPC after the player mines the floor out from under them is an
accepted gap (see README "How NPCs work").
"""
from game.entities.entity import Entity
from game.npcs.npc_def import NpcDef
from game.settings import TILE_SIZE, NPC_WIDTH_TILES, NPC_HEIGHT_TILES


class Npc(Entity):
    def __init__(self, npc_def: NpcDef, spawn_x_px: float, spawn_y_px: float):
        super().__init__(
            spawn_x_px, spawn_y_px,
            NPC_WIDTH_TILES * TILE_SIZE, NPC_HEIGHT_TILES * TILE_SIZE,
        )
        self.npc_def = npc_def
        self.dialogue_index = 0

    def advance_dialogue(self) -> None:
        lines = self.npc_def.dialogue
        if not lines:
            return
        self.dialogue_index = (self.dialogue_index + 1) % len(lines)

    @property
    def current_line(self) -> str:
        lines = self.npc_def.dialogue
        if not lines:
            return ""
        return lines[self.dialogue_index % len(lines)]
