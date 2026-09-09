"""A tiny on-screen message queue: recipe-unlock announcements and
blocked-action hints ("Requires a Pickaxe"), shown one at a time at the top
of the screen. Kept as its own module (not gameplay logic, not rendering)
so both `GameApp` and `InputHandler` can push to it without depending on
`Renderer`.
"""
from dataclasses import dataclass
from typing import Optional

from game.settings import NOTIFICATION_DURATION_S, NOTIFICATION_THROTTLE_S


@dataclass
class _Notification:
    text: str
    remaining_s: float


class NotificationQueue:
    def __init__(self):
        self._queue = []
        self._current: Optional[_Notification] = None
        self._last_text: Optional[str] = None
        self._last_pushed_at_s = -1e9
        self._elapsed_s = 0.0

    def push(self, text: str) -> None:
        """Queues a message; shown after whatever's currently displayed
        finishes. Unthrottled -- use push_throttled for messages that might
        otherwise repeat every frame (e.g. a held-down blocked mining
        attempt)."""
        self._queue.append(_Notification(text, NOTIFICATION_DURATION_S))

    def push_throttled(self, text: str) -> None:
        """Like push, but suppressed if the *same* text was pushed within
        NOTIFICATION_THROTTLE_S -- for messages a caller might otherwise
        fire every single frame (holding the mine button on a tile you
        can't break yet)."""
        if text == self._last_text and (self._elapsed_s - self._last_pushed_at_s) < NOTIFICATION_THROTTLE_S:
            return
        self._last_text = text
        self._last_pushed_at_s = self._elapsed_s
        self.push(text)

    def update(self, dt: float) -> None:
        self._elapsed_s += dt
        if self._current is not None:
            self._current.remaining_s -= dt
            if self._current.remaining_s <= 0.0:
                self._current = None
        if self._current is None and self._queue:
            self._current = self._queue.pop(0)

    @property
    def current_text(self) -> Optional[str]:
        return self._current.text if self._current is not None else None

    @property
    def current_progress(self) -> float:
        """1.0 -> just shown, 0.0 -> about to disappear. For a fade-out."""
        if self._current is None:
            return 0.0
        return max(0.0, min(1.0, self._current.remaining_s / NOTIFICATION_DURATION_S))
