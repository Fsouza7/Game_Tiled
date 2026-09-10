"""A small, generic particle system for short-lived cosmetic effects:
footstep/landing Dust, a Checkpoint-activation/craft-completion Confetti
burst (see assets/Other/), and a procedurally-drawn combat Hit Spark (no
source art exists for this one, so it's drawn as fading radial streaks in
Renderer._draw_particles instead of a sprite -- same "no art, draw it"
precedent as the melee swing arc). No gameplay logic reads particle state
-- purely visual.

The player's ever-present ground shadow (also from assets/Other/) is
deliberately *not* implemented through this system: it isn't a short-lived
effect, it's a persistent decal that exists as long as its owner does, so
it's drawn directly in Renderer._draw_player/_draw_enemies instead of being
spawned/expired here.

Velocities are px/tick (added directly, not dt-scaled), matching every
other physical value in this project (see README "Velocity units");
lifetime is real seconds, like the invulnerability/attack-cooldown timers.
"""
import math
import random
from dataclasses import dataclass
from typing import List, Tuple

from game.settings import (
    GRAVITY, PARTICLE_DUST_LIFETIME_S, PARTICLE_CONFETTI_LIFETIME_S, PARTICLE_CONFETTI_COUNT,
    PARTICLE_HIT_SPARK_LIFETIME_S, PARTICLE_HIT_SPARK_COUNT,
)

DUST = "dust"
CONFETTI = "confetti"
HIT_SPARK = "hit_spark"

# assets/Other/Confetti (16x16).png is a 6-frame strip, each frame already a
# distinctly colored confetti piece -- picking a random *frame* per particle
# gives the color variety instead of re-tinting a single frame at runtime.
CONFETTI_FRAME_COUNT = 6

_GRAVITY_SCALE_BY_KIND = {DUST: 0.15, CONFETTI: 0.35, HIT_SPARK: 0.0}


@dataclass
class Particle:
    x: float
    y: float
    x_vel: float
    y_vel: float
    lifetime: float
    max_lifetime: float
    kind: str
    frame_index: int = 0
    color: Tuple[int, int, int] = (255, 255, 255)  # only read by HIT_SPARK


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def spawn_dust(self, x: float, y: float, count: int = 3) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                x_vel=random.uniform(-0.8, 0.8), y_vel=random.uniform(-1.2, -0.3),
                lifetime=PARTICLE_DUST_LIFETIME_S, max_lifetime=PARTICLE_DUST_LIFETIME_S,
                kind=DUST,
            ))

    def spawn_confetti(self, x: float, y: float, count: int = PARTICLE_CONFETTI_COUNT) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                x_vel=random.uniform(-3.5, 3.5), y_vel=random.uniform(-6.0, -2.0),
                lifetime=PARTICLE_CONFETTI_LIFETIME_S, max_lifetime=PARTICLE_CONFETTI_LIFETIME_S,
                kind=CONFETTI, frame_index=random.randrange(CONFETTI_FRAME_COUNT),
            ))

    def spawn_hit_spark(self, x: float, y: float, color: Tuple[int, int, int], count: int = PARTICLE_HIT_SPARK_COUNT) -> None:
        """A small radial burst at a landed hit's position -- color
        distinguishes a hit the player took (see damage_numbers.
        PLAYER_HIT_COLOR) from one they dealt (ENEMY_HIT_COLOR), the same
        split the floating damage number itself already uses."""
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(2.0, 4.5)
            self.particles.append(Particle(
                x=x, y=y,
                x_vel=math.cos(angle) * speed, y_vel=math.sin(angle) * speed,
                lifetime=PARTICLE_HIT_SPARK_LIFETIME_S, max_lifetime=PARTICLE_HIT_SPARK_LIFETIME_S,
                kind=HIT_SPARK, color=color,
            ))

    def update(self, dt: float) -> None:
        survivors = []
        for p in self.particles:
            p.lifetime -= dt
            if p.lifetime <= 0.0:
                continue
            p.x += p.x_vel
            p.y += p.y_vel
            p.y_vel += GRAVITY * _GRAVITY_SCALE_BY_KIND.get(p.kind, 0.35)
            survivors.append(p)
        self.particles = survivors
