"""A small, generic particle system for short-lived cosmetic effects:
footstep/landing Dust and a Checkpoint-activation Confetti burst (see
assets/Other/). No gameplay logic reads particle state -- purely visual,
same spirit as the melee swing arc in renderer.py.

The player's ever-present ground shadow (also from assets/Other/) is
deliberately *not* implemented through this system: it isn't a short-lived
effect, it's a persistent decal that exists as long as its owner does, so
it's drawn directly in Renderer._draw_player/_draw_enemies instead of being
spawned/expired here.

Velocities are px/tick (added directly, not dt-scaled), matching every
other physical value in this project (see README "Velocity units");
lifetime is real seconds, like the invulnerability/attack-cooldown timers.
"""
import random
from dataclasses import dataclass
from typing import List

from game.settings import GRAVITY, PARTICLE_DUST_LIFETIME_S, PARTICLE_CONFETTI_LIFETIME_S, PARTICLE_CONFETTI_COUNT

DUST = "dust"
CONFETTI = "confetti"

# assets/Other/Confetti (16x16).png is a 6-frame strip, each frame already a
# distinctly colored confetti piece -- picking a random *frame* per particle
# gives the color variety instead of re-tinting a single frame at runtime.
CONFETTI_FRAME_COUNT = 6


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

    def update(self, dt: float) -> None:
        survivors = []
        for p in self.particles:
            p.lifetime -= dt
            if p.lifetime <= 0.0:
                continue
            p.x += p.x_vel
            p.y += p.y_vel
            p.y_vel += GRAVITY * (0.15 if p.kind == DUST else 0.35)
            survivors.append(p)
        self.particles = survivors
