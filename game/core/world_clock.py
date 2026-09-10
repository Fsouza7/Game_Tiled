"""Day/night clock. A pure timekeeper -- it has no idea lighting or enemy
spawning read it, it just tracks time and derives an ambient light curve.
"""
import math

from game.settings import (
    DAY_LENGTH_S, DAY_MAX_AMBIENT, NIGHT_MIN_AMBIENT, NIGHT_LIGHT_THRESHOLD,
    MORNING_TIME_OF_DAY_FRACTION,
)


class WorldClock:
    def __init__(self):
        self.time_of_day = DAY_LENGTH_S * MORNING_TIME_OF_DAY_FRACTION  # start mid-morning, not at midnight
        self.day_count = 1

    def update(self, dt: float) -> None:
        self.time_of_day += dt
        if self.time_of_day >= DAY_LENGTH_S:
            self.time_of_day -= DAY_LENGTH_S
            self.day_count += 1

    def skip_to_morning(self) -> None:
        """Sleeping in a Bed: jumps straight to the next morning, always
        forward in time -- if it's already past dawn today (afternoon,
        evening, night), that means tomorrow's dawn and the day count
        ticks up; if it's earlier than dawn (the small early-morning
        window before MORNING_TIME_OF_DAY_FRACTION), that means later
        today, same day count."""
        dawn = DAY_LENGTH_S * MORNING_TIME_OF_DAY_FRACTION
        if self.time_of_day >= dawn:
            self.day_count += 1
        self.time_of_day = dawn

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
