"""Day/night clock. A pure timekeeper -- it has no idea lighting or enemy
spawning read it, it just tracks time and derives an ambient light curve.
"""
import math

from game.settings import DAY_LENGTH_S, DAY_MAX_AMBIENT, NIGHT_MIN_AMBIENT, NIGHT_LIGHT_THRESHOLD


class WorldClock:
    def __init__(self):
        self.time_of_day = DAY_LENGTH_S * 0.3  # start mid-morning, not at midnight
        self.day_count = 1

    def update(self, dt: float) -> None:
        self.time_of_day += dt
        if self.time_of_day >= DAY_LENGTH_S:
            self.time_of_day -= DAY_LENGTH_S
            self.day_count += 1

    @property
    def progress(self) -> float:
        """0.0 = midnight, 0.5 = noon, wrapping back to 1.0 = midnight."""
        return self.time_of_day / DAY_LENGTH_S

    @property
    def ambient_light(self) -> float:
        """Smooth (cosine) brightness curve: darkest at midnight, brightest
        at noon, gradually transitioning through dawn/dusk in between --
        no discrete "lights just switched off" jump."""
        wave = 0.5 - 0.5 * math.cos(2 * math.pi * self.progress)  # 0 at midnight, 1 at noon
        return NIGHT_MIN_AMBIENT + (DAY_MAX_AMBIENT - NIGHT_MIN_AMBIENT) * wave

    @property
    def is_night(self) -> bool:
        return self.ambient_light < NIGHT_LIGHT_THRESHOLD

    def clock_string(self) -> str:
        """A human-readable HH:MM for the HUD, purely cosmetic."""
        total_minutes = int(self.progress * 24 * 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"
