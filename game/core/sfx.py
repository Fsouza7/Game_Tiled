"""Procedurally synthesized sound effects -- no audio files. Same "no art,
draw it" precedent particles.py/renderer.py already use for the Hit Spark
and the melee swing arc, applied to audio: every sound here is a short PCM
waveform built at startup from sine/square/triangle tones and noise
bursts (pure stdlib -- `array` + `math` + `random`, no numpy).

pygame's mixer is usually stereo (see pygame.mixer.get_init()) but isn't
guaranteed to be -- a buffer handed to Sound(buffer=...) is interpreted
strictly according to however many channels the live mixer session
actually has, and a mismatched channel count is silently misread as a
different sample count entirely, playing back at the wrong speed/pitch
with channels swapped. Every waveform below is synthesized mono (simpler
math) and duplicated out to however many channels the mixer actually
reports (_output_channels/_duplicate_channels) only in the final
Sound-construction step, rather than assuming 2.

Only the raw PCM *bytes* are cached (in init(), once per process) -- never
a pygame.mixer.Sound object. A Sound is bound to whichever mixer session
(SDL_mixer instance) was active when it was constructed; playing one after
that session has since been torn down (pygame.quit(), e.g. a real game
restart, or -- concretely -- what this project's own test suite does
between tests that each build their own GameApp) is a native
use-after-free -- an access violation, not a Python exception play() could
catch. Plain bytes have no such session binding, so play() constructs a
fresh, cheap Sound from them (no re-synthesis) against whatever mixer is
actually active at that exact moment, every single call.
"""
import array
import logging
import math
import random
from typing import Dict, List

import pygame

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100
_MAX_AMPLITUDE = 32767

_sound_bytes: Dict[str, bytes] = {}  # process-lifetime cache, mixer-session-independent (see module docstring)


def _envelope(n: int, attack: int, release: int) -> List[float]:
    """A 0..1 gain curve: linear fade in over `attack` samples, full
    volume in between, linear fade out over the last `release` samples --
    without this, a tone starting/stopping mid-waveform pops audibly."""
    env = [1.0] * n
    attack = min(attack, n // 2)
    release = min(release, n // 2)
    for i in range(attack):
        env[i] = i / attack
    for i in range(release):
        env[n - 1 - i] = i / release
    return env


def _wave_sample(phase: float, wave: str) -> float:
    if wave == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    if wave == "triangle":
        return 2.0 / math.pi * math.asin(math.sin(phase))
    return math.sin(phase)


def _tone(freq: float, duration_s: float, volume: float = 0.5, wave: str = "sine") -> array.array:
    n = int(SAMPLE_RATE * duration_s)
    env = _envelope(n, attack=int(SAMPLE_RATE * 0.005), release=int(SAMPLE_RATE * 0.02))
    samples = array.array("h", [0]) * n
    for i in range(n):
        phase = 2 * math.pi * freq * (i / SAMPLE_RATE)
        samples[i] = int(_wave_sample(phase, wave) * volume * env[i] * _MAX_AMPLITUDE)
    return samples


def _sweep(freq_start: float, freq_end: float, duration_s: float, volume: float = 0.5, wave: str = "sine") -> array.array:
    """Like _tone, but the pitch glides linearly from freq_start to
    freq_end -- a "whoosh" (swing/shot) or a falling "thud" (a hit taken),
    depending on direction."""
    n = int(SAMPLE_RATE * duration_s)
    env = _envelope(n, attack=int(SAMPLE_RATE * 0.003), release=int(SAMPLE_RATE * 0.02))
    samples = array.array("h", [0]) * n
    phase = 0.0
    for i in range(n):
        freq = freq_start + (freq_end - freq_start) * (i / n)
        phase += 2 * math.pi * freq / SAMPLE_RATE
        samples[i] = int(_wave_sample(phase, wave) * volume * env[i] * _MAX_AMPLITUDE)
    return samples


def _noise_burst(duration_s: float, volume: float = 0.5, seed: int = 0) -> array.array:
    """White noise with an instant attack and a full decay -- an impact/
    crunch, not a tone. `seed` keeps a given call site's texture
    consistent across runs rather than re-rolling static every time."""
    n = int(SAMPLE_RATE * duration_s)
    env = _envelope(n, attack=int(SAMPLE_RATE * 0.002), release=n)
    rng = random.Random(seed)
    samples = array.array("h", [0]) * n
    for i in range(n):
        samples[i] = int(rng.uniform(-1.0, 1.0) * volume * env[i] * _MAX_AMPLITUDE)
    return samples


def _concat(*parts: array.array) -> array.array:
    out = array.array("h")
    for p in parts:
        out.extend(p)
    return out


def _mix(*parts: array.array) -> array.array:
    length = max(len(p) for p in parts)
    out = array.array("h", [0]) * length
    for p in parts:
        for i, v in enumerate(p):
            out[i] = max(-32768, min(32767, out[i] + v))
    return out


def _duplicate_channels(mono: array.array, channels: int) -> array.array:
    """Interleaves `mono` into `channels` identical channels -- pygame's
    mixer *usually* defaults to stereo (2), but doesn't have to (some real
    audio devices/drivers negotiate something else), and Sound(buffer=...)
    interprets a buffer strictly according to whatever the live mixer
    session's own channel count is. Reading it at synthesis time instead
    of hardcoding 2 keeps a buffer size/format mismatch from ever being
    the reason a sound effect fails to play."""
    if channels <= 1:
        return mono
    out = array.array("h", [0]) * (len(mono) * channels)
    for c in range(channels):
        out[c::channels] = mono
    return out


def _output_channels() -> int:
    init_info = pygame.mixer.get_init()
    return init_info[2] if init_info is not None else 2


def _build_sound_bank() -> Dict[str, array.array]:
    """One mono waveform per effect. Volumes are kept low (0.18-0.32) and
    relative to each other -- these play often, sometimes several per
    second (mining), so nothing here should fight the background music
    or fatigue the ear on repeat."""
    return {
        "mine_tick": _noise_burst(0.05, volume=0.16, seed=1),
        "mine_break": _mix(_noise_burst(0.12, volume=0.3, seed=2), _tone(110, 0.1, volume=0.22, wave="triangle")),
        "melee_swing": _sweep(900, 300, 0.09, volume=0.2, wave="triangle"),
        "ranged_shoot": _sweep(500, 1100, 0.07, volume=0.2, wave="square"),
        "hit_player": _mix(_noise_burst(0.14, volume=0.28, seed=3), _sweep(260, 90, 0.14, volume=0.26, wave="square")),
        "hit_enemy": _tone(700, 0.06, volume=0.2, wave="square"),
        "craft_complete": _concat(_tone(523, 0.07, volume=0.2, wave="triangle"), _tone(784, 0.09, volume=0.22, wave="triangle")),
        "smelt_complete": _concat(_tone(440, 0.07, volume=0.18, wave="triangle"), _tone(659, 0.09, volume=0.2, wave="triangle")),
        "level_up": _concat(
            _tone(523, 0.08, volume=0.22, wave="triangle"), _tone(659, 0.08, volume=0.22, wave="triangle"),
            _tone(784, 0.08, volume=0.22, wave="triangle"), _tone(1047, 0.16, volume=0.26, wave="triangle"),
        ),
        "chest_open": _concat(_tone(392, 0.06, volume=0.18, wave="sine"), _tone(523, 0.1, volume=0.2, wave="sine")),
    }


def init() -> None:
    """Synthesizes every effect's raw waveform bytes once per process
    (see module docstring for why only the bytes are cached, never a
    Sound object) -- called from GameApp.__init__ alongside music.py, but
    safe to call any number of times; every call after the first is a
    no-op. Missing/broken synthesis degrades to silence rather than
    crashing the game, same precedent as music.py and missing art in
    assets.py."""
    global _sound_bytes
    if _sound_bytes:
        return
    try:
        bank = _build_sound_bank()
        channels = _output_channels()
        _sound_bytes = {key: _duplicate_channels(samples, channels).tobytes() for key, samples in bank.items()}
    except Exception:
        logger.warning("Failed to synthesize sound effects", exc_info=True)


def play(key: str) -> None:
    """Builds a fresh Sound from the cached bytes and plays it immediately
    -- see the module docstring for why a Sound is never itself cached.
    Silently does nothing if init() was never called, the key doesn't
    exist, or there's no live mixer session right now (e.g. headless
    tests, or a machine with no audio device).

    Deliberately catches *any* exception, not just pygame.error: this is
    called from the middle of core gameplay code (Player.try_mine,
    combat_system, InputHandler chest-opening, GameApp's crafting/level-up
    hooks) with nothing else between it and GameApp's main loop, so an
    unusual real-world audio driver/device quirk raising something other
    than pygame.error must never be allowed to take down mining, chest
    interaction, or crafting -- audio is enhancement, not core
    functionality, and should degrade to silence, never crash gameplay."""
    data = _sound_bytes.get(key)
    if data is None or not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.Sound(buffer=data).play()
    except Exception:
        logger.debug("Could not play sfx %r", key, exc_info=True)
