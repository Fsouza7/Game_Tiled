"""Deterministic, tile-grid-independent moving hazards: Saw, Rock Head,
Spike Head, Spiked Ball.

Each is anchored to a fixed world position rolled once, deterministically,
during chunk generation (see `world_generator.generate_hazard_anchor`) and
its current position is a pure function of elapsed world time (a sine
oscillation) -- no per-frame mutable state to track, consistent with how
the rest of world generation works (see README "Determinism"): a chunk can
be unloaded and regenerated later and its hazards reappear in exactly the
same place, doing exactly what they'd be doing at that moment in time.

This is a deliberate simplification of the source material: a "real" Rock
Head/Spike Head trap charges at the player once triggered by proximity,
which would require tracking per-hazard trigger/charge/return state and
colliding the charge against the static tile grid. Instead these swing/
thump on a fixed rhythm the player has to time a pass around -- still a
real hazard, just stateless and independent of chunk load order.
"""
from dataclasses import dataclass
import math

import pygame

from game.settings import (
    TILE_SIZE,
    SAW_CONTACT_DAMAGE, SAW_AMPLITUDE_TILES, SAW_PERIOD_S,
    ROCK_HEAD_CONTACT_DAMAGE, ROCK_HEAD_AMPLITUDE_TILES, ROCK_HEAD_PERIOD_S,
    SPIKE_HEAD_CONTACT_DAMAGE, SPIKE_HEAD_AMPLITUDE_TILES, SPIKE_HEAD_PERIOD_S,
    SPIKED_BALL_CONTACT_DAMAGE, SPIKED_BALL_AMPLITUDE_TILES, SPIKED_BALL_PERIOD_S,
)

SAW = "saw"
ROCK_HEAD = "rock_head"
SPIKE_HEAD = "spike_head"
SPIKED_BALL = "spiked_ball"

ALL_KINDS = (SAW, ROCK_HEAD, SPIKE_HEAD, SPIKED_BALL)

# kind -> (contact_damage, amplitude_tiles, period_s, oscillation axis, width_tiles, height_tiles)
_KIND_PARAMS = {
    SAW: (SAW_CONTACT_DAMAGE, SAW_AMPLITUDE_TILES, SAW_PERIOD_S, "y", 0.9, 0.9),
    ROCK_HEAD: (ROCK_HEAD_CONTACT_DAMAGE, ROCK_HEAD_AMPLITUDE_TILES, ROCK_HEAD_PERIOD_S, "y", 1.0, 1.0),
    SPIKE_HEAD: (SPIKE_HEAD_CONTACT_DAMAGE, SPIKE_HEAD_AMPLITUDE_TILES, SPIKE_HEAD_PERIOD_S, "x", 1.1, 1.05),
    # A "real" spiked ball swings side to side, pendulum-style; this one
    # bobs vertically instead, reusing Saw's exact chain-and-oscillation
    # rendering unchanged rather than adding arc/angle math for one hazard.
    SPIKED_BALL: (SPIKED_BALL_CONTACT_DAMAGE, SPIKED_BALL_AMPLITUDE_TILES, SPIKED_BALL_PERIOD_S, "y", 0.8, 0.8),
}


@dataclass(frozen=True)
class HazardAnchor:
    kind: str
    anchor_x: float  # world px, tile-center
    anchor_y: float  # world px, tile-center
    phase: float  # radians, randomized per-anchor so hazards don't all sync

    @property
    def contact_damage(self) -> float:
        return _KIND_PARAMS[self.kind][0]

    def current_center(self, elapsed_s: float):
        _, amplitude_tiles, period_s, axis, _, _ = _KIND_PARAMS[self.kind]
        offset = amplitude_tiles * TILE_SIZE * math.sin(2 * math.pi * elapsed_s / period_s + self.phase)
        if axis == "y":
            return self.anchor_x, self.anchor_y + offset
        return self.anchor_x + offset, self.anchor_y

    def oscillation_progress(self, elapsed_s: float) -> float:
        """-1..1, how close to the far extreme of its swing right now --
        used by the renderer to pick an idle vs. "impact" sprite frame."""
        _, _, period_s, _, _, _ = _KIND_PARAMS[self.kind]
        return math.sin(2 * math.pi * elapsed_s / period_s + self.phase)

    def current_rect(self, elapsed_s: float) -> pygame.Rect:
        _, _, _, _, width_tiles, height_tiles = _KIND_PARAMS[self.kind]
        cx, cy = self.current_center(elapsed_s)
        w, h = width_tiles * TILE_SIZE, height_tiles * TILE_SIZE
        return pygame.Rect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
