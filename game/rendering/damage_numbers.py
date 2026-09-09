"""World-space floating damage numbers. Purely visual -- spawned from
Player/Enemy.take_damage via GameApp, drawn by Renderer. Not persisted
(same as particles/notifications).
"""
import random
from dataclasses import dataclass
from typing import List, Tuple

from game.settings import DAMAGE_POPUP_LIFETIME_S, DAMAGE_POPUP_RISE_PX_PER_S

# Player-taken hits read as incoming harm (red); damage dealt to enemies
# reads as a scored hit (gold). Same "one look tells you who got hurt"
# split every ARPG uses.
PLAYER_HIT_COLOR = (255, 85, 75)
ENEMY_HIT_COLOR = (255, 225, 90)


@dataclass
class DamagePopup:
    x: float
    y: float
    amount: float
    on_player: bool
    lifetime: float
    max_lifetime: float
    x_vel: float  # px/second, a tiny drift so stacked hits don't overlap


class DamageNumbers:
    def __init__(self):
        self.popups: List[DamagePopup] = []

    def spawn(self, x: float, y: float, amount: float, on_player: bool = False) -> None:
        if amount <= 0:
            return
        self.popups.append(DamagePopup(
            x=x, y=y, amount=amount, on_player=on_player,
            lifetime=DAMAGE_POPUP_LIFETIME_S, max_lifetime=DAMAGE_POPUP_LIFETIME_S,
            x_vel=random.uniform(-18.0, 18.0),
        ))

    def update(self, dt: float) -> None:
        survivors = []
        for popup in self.popups:
            popup.lifetime -= dt
            if popup.lifetime <= 0.0:
                continue
            popup.x += popup.x_vel * dt
            popup.y -= DAMAGE_POPUP_RISE_PX_PER_S * dt
            survivors.append(popup)
        self.popups = survivors


def queue_popup(entity, amount: float) -> None:
    """Records a hit at the entity's current position so a later respawn
    or death doesn't move the number (fall-damage deaths teleport the
    player to spawn in the same take_damage call)."""
    if amount <= 0:
        return
    entity.pending_damage_popups.append((entity.center_x, entity.y, amount))


def drain_popups(entity) -> List[Tuple[float, float, float]]:
    pops = entity.pending_damage_popups
    entity.pending_damage_popups = []
    return pops
