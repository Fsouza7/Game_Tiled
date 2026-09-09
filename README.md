# Sandbox Prototype

A 2D sandbox exploration/mining/building game, built incrementally in
phases. Inspired by the genre popularized by Terraria/Starbound/Minecraft,
with an original tile set, world generator and code base -- no third-party
game code, names or maps are reused. Real sprite art from the bundled
`assets/` pack *is* reused for visuals (tiles, player, items -- see "Art
reuse" below); none of it drives gameplay data, and every reuse is
documented rather than pretended away.

> **Status: Phase 6 (biomes) + Deferred-assets pass 2 + Crafting UX pass**
> — see `TODO.md` for the full roadmap and what is/isn't implemented yet.

This repository also contains an older, unrelated fixed-level platformer
prototype (`Objects/`, `Logics/`, root `settings.py`/`setup.py`). It is kept
as-is and is **not** part of the sandbox game described below, which lives
entirely under `game/`.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.9+ and Pygame 2.5+.

## Run

```bash
python -m game.main
```

Optional: pick a specific world seed (same seed = same world every time):

```bash
SANDBOX_SEED=12345 python -m game.main      # bash
$env:SANDBOX_SEED=12345; python -m game.main # PowerShell
```

## Run tests

```bash
python -m pytest tests/ -v
```

Tests run headlessly (no real window needed) via `SDL_VIDEODRIVER=dummy`,
set automatically in `tests/conftest.py`. They cover world generation
determinism, tile layers, mining (with/without the required tool),
building, inventory stacking, player physics/fall damage/respawn/health
regen, camera clamping, chunk load/unload, item catalog coverage, crafting
(ingredient/station gating, the craft transaction, refund-on-full-inventory,
section grouping and scroll clamping in the crafting UI), combat (enemy AI
collision probes, melee/ranged attacks, projectiles, contact damage/
invulnerability, the spawner's population cap), equipment (equip/unequip
transactions, defense reducing combat damage, UI slot layout), and the
world cycle (the day/night ambient curve, point-light falloff/radius/
bounds, the torch item/tile/recipe, night-exclusive enemy spawning),
biomes (deterministic seed-consistent zoning, the always-Forest spawn
window, per-biome ground tiles and underground stone/exclusive gem ores,
desert cacti replacing trees, the biome-exclusive enemy), food/hazards
(eating heals and consumes the item, is a no-op at full health or on
non-food, the Berry Bush's random-fruit drop, Spikes contact damage with
its invulnerability window, the Trampoline bounce overriding fall damage),
the second deferred-assets pass (character registry/asset coverage,
Fan updraft range, Sand/Mud/Ice speed multipliers, Falling Platform
crumble/respawn/timer-reset, Checkpoint activation/respawn, moving-hazard
spawn coverage/oscillation/contact damage, particle expiry), and the
crafting UX pass (recipe discovery locking/unlocking and the newly-
discovered-recipe diff, the blocked-mining message for every reach/tool
case, and the furnace's start/busy/complete/restart smelt-job lifecycle).

## Controls

A one-time character-select screen appears at startup: click a portrait (or
Left/Right to change the highlight), Enter/Space to confirm. Everything
below applies once you're in the world.

| Action | Key |
|---|---|
| Move left/right | A/D or Arrow keys |
| Jump (press again mid-air for a double jump) | Space |
| Mine / break block | Left mouse (hold) |
| Place block | Right mouse |
| Select hotbar slot | 1-9 |
| Eat the selected food item (heals HP) | F |
| Zoom in/out | Mouse wheel, or +/- |
| Open/close inventory & equipment | E |
| Equip an armor piece (while inventory is open) | Left-click it in the bag |
| Unequip an armor piece (while inventory is open) | Left-click its equipment slot |
| Open/close crafting | C |
| Craft a recipe / start a smelt job (while crafting is open) | Left-click its row |
| Scroll the crafting list (while crafting is open) | Mouse wheel |
| Attack (melee or ranged -- select a weapon in the hotbar first) | Left-click |
| Pause (opens a real menu: Resume/Settings/Restart/Quit) | Esc |
| Debug overlay (FPS, pos, chunk, seed, enemy count, day/time/ambient) | F3 |

Combat: with any weapon selected, the character continuously faces the
mouse cursor (a small crosshair reticle marks the aim point -- yellow for
melee, red for ranged) so the swing/shot direction is never a surprise.
With a melee weapon (Wood Sword) selected, left-click swings in a
`MELEE_ARC_DEGREES`-wide cone centered on the cursor -- it hits whatever
the mouse points at, not just strictly left/right -- and plays a brief
slash-arc visual in that direction. With a ranged weapon (Wood Bow)
selected and arrows in your inventory, left-click fires an arrow straight
at the cursor. Left-click only mines/attacks -- whichever the selected item
supports -- so mining is automatically disabled while a weapon is selected.

## Architecture

```
game/
  settings.py        # every tunable constant lives here, nothing hardcoded elsewhere
  main.py             # entry point
  world/
    tile.py            # TileDef schema (id, solidity, resistance, drops, light fields, ...)
    tile_registry.py    # every tile type, one entry each (add tiles here)
    chunk.py            # one vertical slice of the world (CHUNK_WIDTH columns x full height)
    world.py             # chunk lifecycle (lazy load/unload), tile get/break/place, bounds
    world_generator.py    # deterministic, seed-based terrain/cave/ore/biome/vegetation generation
    biome.py               # BiomeDef schema (surface/subsurface tiles, spawn weight)
    biome_registry.py       # every biome, one entry each (add biomes here)
    lighting.py            # point-light + ambient brightness, computed only for the visible viewport
    hazard_feature.py       # Saw/Rock Head/Spike Head: anchor + sine-oscillation position, pure function of elapsed time
    checkpoints.py          # Checkpoint touch -> new respawn point (kept out of GameApp so it's unit-testable)
  items/
    item.py             # full ItemDef schema (category, rarity, value, damage, durability, ...)
    item_registry.py     # every item type, one entry each (add items here)
  inventory/
    inventory.py        # slots, stacking, hotbar selection, add/remove
    equipment.py         # RPG-style armor slots (head/body): equip/unequip, total defense
  crafting/
    recipe.py           # RecipeDef schema (ingredients, result, optional station)
    recipe_registry.py   # every recipe, one entry each (add recipes here)
    crafting_system.py   # ingredient/station checks, the craft transaction, and recipe-discovery logic (no UI code)
    smelt_recipe.py       # SmeltRecipeDef schema (ore+fuel -> bar, over time)
    smelt_registry.py      # every smelt recipe, one entry each (add ore->bar pairs here)
    furnace_system.py       # FurnaceManager: start/track/complete timed smelt jobs, keyed by furnace tile
  entities/
    entity.py           # position/size/velocity base class
    tile_collision.py    # shared AABB-vs-tile-grid movement, used by Player and Enemy alike
    player.py            # movement, gravity, tile collision, health, fall damage, mining, combat state
    character_registry.py # every playable character skin, one entry each (add characters here)
    enemy_def.py          # EnemyDef schema (health, damage, speed, AI type, drops)
    enemy_registry.py     # every enemy type, one entry each (add enemies here)
    enemy.py              # runtime enemy instance (health, i-frames, drop roll) -- no AI logic
    enemy_ai.py            # the three AI behaviors (walk/hop/fly), pure functions over (enemy, world, player, dt)
    enemy_spawner.py        # periodic spawning near the player, population cap, despawn-when-far
  combat/
    projectile.py        # a fired projectile (arrow): straight-line + light gravity arc
    combat_system.py      # melee/ranged attack resolution, projectile updates, contact damage, knockback
  core/
    camera.py           # smooth follow + world-bound clamping + zoom
    debug_overlay.py     # F3 HUD
    world_clock.py        # day/night timekeeper; derives the ambient light curve
    notifications.py      # small FIFO toast queue (recipe unlocks, blocked-mining messages)
    game_app.py          # the game loop; wires world/player/camera/input/renderer together
  input/
    input_handler.py    # keyboard/mouse -> game actions (the only file that knows key bindings)
  rendering/
    renderer.py          # draws world/player/HUD/inventory+equipment panel/crafting panel; no gameplay logic
    assets.py            # loads/slices real art and builds procedural textures+icons
    particles.py          # Dust/Confetti: a small generic spawn/update/expire particle system
tests/
  test_phase1_smoke.py  # headless functional tests for everything above
```

Design choices worth knowing about:

- **Velocity units**: `x_vel`/`y_vel` on every physical entity (Player,
  Enemy, Projectile) are **px added per game-loop tick**, not px/second --
  they're added directly in `tile_collision.move_axis` without any `dt`
  scaling, matching `GRAVITY`/`PLAYER_MOVE_SPEED`/`PLAYER_JUMP_VELOCITY` in
  `settings.py`. Only real-time countdowns (mining progress, attack
  cooldowns, invulnerability timers, projectile lifetime) use `dt`. Mixing
  the two (e.g. multiplying a velocity by `TILE_SIZE` to turn "tiles/sec"
  into pixels, or by `dt` when integrating position) produces speeds off by
  10-100x -- this bit Phase 4's first draft (knockback/projectile/enemy
  speed constants) and is worth remembering before adding new movement.
- **Chunking**: the world is split into column chunks (`CHUNK_WIDTH` tiles
  wide, full world height). Chunks are generated lazily the first time
  they're needed and unloaded once far from the player, so cost scales with
  what's been explored, not with total world size.
- **Determinism**: `world_generator.py` computes every tile as a pure
  function of `(seed, x, y)` — no dependency on neighboring columns or the
  order chunks are generated in. That's what makes lazy loading safe and
  the same seed reproducible.
- **Art reuse**: tiles are sliced from `assets/Terrain/Terrain.png` and the
  player uses the `assets/MainCharacters/NinjaFrog` sprite sheets (both
  already present in this repo). Only grass, dirt and one stone-brick tile
  have dedicated art in that sheet; everything else (ore, bedrock,
  workbench, tree trunk/leaves, planks) reuses the closest base sprite with
  a color tint *plus* a small procedural detail -- speckles for ore,
  bark/plank lines, a tabletop band for the workbench -- so it reads as a
  distinct material instead of a flat color wash (see
  `game/rendering/assets.py`). A tile with no mapped texture at all falls
  back to its `TileDef.color` as a flat rectangle. The same idea applies to
  item icons: a block/ore/material icon reuses its tile's texture
  (`ItemDef.places_tile_id`/`icon_tile_id`); the handful of items with
  neither a tile nor sprite to borrow (pickaxes, sword, bow, arrow, helmet,
  armor -- this asset pack has no tool/weapon/armor icons) get a small
  hand-drawn vector icon instead of an anonymous color swatch.

## How to add a new tile

Add one `TileDef` entry in `game/world/tile_registry.py` (pick an unused
`id`, fill in `color`, `solid`, `resistance`, `required_tool`,
`drop_item_id`, `can_place`, `can_break`). If it drops a new item, add that
item to `game/items/item_registry.py` first. To give it real art, add a
`(column, row)` entry for its id to `_TERRAIN_CELLS` in
`game/rendering/assets.py` (16x16 cell coordinates in `Terrain.png`) --
otherwise it renders as a flat rectangle in its `TileDef.color`. To make it
a light source, set `light_emit` (0-15, see "How the day/night cycle and
lighting work" below) -- no other file needs to change, `lighting.py`
already scans every tile's `light_emit`.

## How to add a new item

Add one `ItemDef` entry in `game/items/item_registry.py` with a `category`
(`ItemCategory.BLOCK/ORE/MATERIAL/TOOL/WEAPON/CONSUMABLE/ARMOR/DECORATION`),
`description`, `rarity` and `value`. Depending on the category:
- **Block/decoration**: set `places_tile_id` to an existing tile id.
- **Tool**: set `is_tool=True`, `mining_power`, `tool_type` (must match a
  `TileDef.required_tool`), and usually `max_durability`.
- **Weapon**: set `is_weapon=True`, `damage`, `speed` (attacks/sec),
  `max_durability` (not yet consumed -- no durability loss is implemented
  yet), and for ranged weapons `is_ranged=True` + `ammo_item_id`.
- **Armor**: set `equip_slot` (must be one of `game/inventory/equipment.py`'s
  `SLOTS`, currently `"head"`/`"body"`) and `defense` (flat damage
  reduction applied in `combat_system.resolve_contact_damage`). Add a new
  body-part slot by adding its name to `SLOTS`; the inventory screen lays
  out one box per slot automatically.
- **Icon**: resolution order is `places_tile_id` (block/decoration -- uses
  the tile's own texture) -> `icon_tile_id` (borrow any tile's texture
  without being placeable, e.g. an ore or raw material) -> `icon_key`
  (looked up in `game/rendering/assets.py`: either a real sprite added to
  `_STATIC_ICON_SOURCES`, or a hand-drawn vector icon added to
  `_build_procedural_icons`) -> a flat color swatch by category as the last
  resort. Prefer `icon_tile_id` over a flat swatch whenever the item
  corresponds to an existing tile.

## How trees work

Trees are generated the same deterministic way as everything else: the
world is divided into fixed-width slots (`TREE_SLOT_WIDTH`), and each slot
independently rolls whether it contains one tree and at which column
(`TREE_SPAWN_CHANCE_PER_SLOT`, in `world_generator.py`). A tree is a 3-tile
trunk (`TREE_TRUNK_ID`) topped with a small canopy (`TREE_LEAVES_ID`)
spanning that column and its two neighbors. Both trunk and leaves drop
`wood` when broken. This keeps the "any column can be generated
independently, in any order" guarantee: a column figures out its own role
(trunk / canopy / none) by re-deriving its slot's roll and its neighbors'
rolls, without needing those columns to already exist.

## How the day/night cycle and lighting work

`WorldClock` (`game/core/world_clock.py`) tracks `time_of_day` in
`[0, DAY_LENGTH_S)` and derives `ambient_light` from a cosine curve --
darkest at midnight (`NIGHT_MIN_AMBIENT`), brightest at noon
(`DAY_MAX_AMBIENT`) -- so there's never a discrete "lights just switched
off" jump, and `is_night` (used for spawning) is just `ambient_light` below
`NIGHT_LIGHT_THRESHOLD`. The sky background is tinted to match (a warm
overlay peaking at dawn/dusk, a navy overlay peaking at midnight, both
derived from the same ambient value, so they can't drift out of sync).

`game/world/lighting.py` computes actual brightness per tile: the brighter
of ambient light and the falloff from any nearby `TileDef.light_emit`
source (currently only the Torch, `light_emit=14`), out to
`LIGHT_RADIUS_TILES` scaled by the source's strength. **Light sources are
only searched for within the visible camera viewport (+
`LIGHT_SEARCH_MARGIN_TILES`) once per frame** -- never the whole world --
so cost is flat regardless of world size (~10ms/frame end-to-end on this
machine with lighting + day/night active). This is a real simplification
over Terraria/Minecraft-style flood-fill lighting: it does **not** respect
occlusion, so a torch shines through a thin wall with a plain distance
falloff rather than stopping at the first solid tile. Tiles get a
rectangular darkness overlay (cheap, they're opaque squares); the player
sprite is darkened via an RGB-only multiply blend that preserves its own
transparency (a plain overlay rectangle would show up as a boxy halo around
the character's silhouette); enemies are flat vector shapes, so their fill
color is dimmed directly.

`WorldClock.ambient_light` is the *sky's* brightness -- what applies at and
above the surface. Below the surface it's no longer the right value on its
own: without adjustment, a cave at noon would be exactly as bright as the
open sky, defeating the entire point of carrying a Torch underground.
`lighting.ambient_light_for_depth(depth_below_surface, sky_ambient)`
handles that: a pure function of how many tiles below `World.surface_height_at(x)`
a position is, it fades the sky's ambient down to `UNDERGROUND_MIN_AMBIENT`
over `UNDERGROUND_DARK_DEPTH_TILES`, floored (never pure black) and
**independent of time of day** -- a cave at noon fades to the same
near-darkness as one at midnight. `Renderer._draw_world/_draw_player/_draw_enemies`
each compute their own local ambient this way (per-column for tiles, per-entity
position for the player/enemies) before calling `light_level_at`, so a torch
still lights up its surroundings underground exactly like it does on the
surface at night -- only now that's true at any hour.

## How health regen works

The player slowly heals over time (`PLAYER_REGEN_RATE_HP_PER_S`) whenever
below max health, but taking any damage (contact or fall) resets a delay
(`PLAYER_REGEN_DELAY_AFTER_DAMAGE_S`) that must fully run out before regen
resumes -- so tanking hits in a fight can't out-heal itself, but downtime
between fights (or while mining/exploring) steadily recovers lost health.
`Player.is_regenerating()` reports whether it's currently active; the
health bar's border pulses green while it is, and F3's debug overlay shows
the countdown when it isn't. This is *passive* healing; for instant healing
via food, see "How eating works" below.

## How eating works

Eight items are real food: `apple` and seven fruits (Banana, Cherries,
Kiwi, Melon, Orange, Pineapple, Strawberry -- `assets/Items/Fruits/`, one
new fruit item per source image in the pack). Each has `ItemDef.heal_amount`
set; pressing `F` calls `Player.eat_selected()`, which heals that much HP
(capped at max) and consumes one from the selected hotbar slot. It's a
no-op at full health (so a food item is never wasted on a full bar) and a
no-op for anything else selected, food or not (`arrow` is also
`ItemCategory.CONSUMABLE` but has `heal_amount=0`, so pressing F with it
selected does nothing -- category alone doesn't imply edibility).

Fruit is obtained from a new rare surface spawn, the Berry Bush
(`BUSH_ID`): like the wooden crate, it competes with the same
no-tree-this-column roll in `_place_forest_decoration` (Forest/Snow/Jungle
only -- Desert's roll is cacti/crates instead, no bushes). Breaking one
drops one random item from `TileDef.drop_pool` -- a new, minimal schema
addition (an ordered tuple of item ids) alongside the existing single-item
`drop_item_id`, since a bush is the first tile that needed "one of several
possible drops" instead of one fixed drop.

## How placeable hazard/bounce tiles work

Two more `assets/Traps/` sprites became real tiles, each via one new
opt-in `TileDef` field (both default to 0/inert, so every existing tile is
unaffected):

- **Spikes** (`contact_damage`): a hazard block. Non-solid (you walk
  through it, you don't stand on it), so `combat_system.resolve_hazard_damage`
  checks every tile the player's hitbox overlaps each frame, the tile
  equivalent of the existing enemy `resolve_contact_damage` -- same
  invulnerability window, same defense reduction, so it can't multi-hit
  the instant you touch it. Originally craftable, it was later redesigned
  into a world-generated environmental hazard -- see "How the
  world-generated traps work" below.
- **Trampoline** (`bounce_velocity`): a craftable bounce pad -- it's a
  fun/traversal tool, not a hazard, so it stayed player-built. Solid (you
  land on it like a floor), but `Player.physics_step` checks the tile
  directly beneath a landing this frame and, if it has a `bounce_velocity`,
  launches upward instead of coming to rest and skips fall damage for that
  landing -- like a soft cushion, not a floor.

## How character select works

`assets/MainCharacters/` has 4 interchangeable skins (Ninja Frog plus Mask
Dude/Pink Man/Virtual Guy) with identical frame sizes and animation
filenames, registered in `game/entities/character_registry.py`. At startup
`GameApp.character_select_open` blocks the normal game loop and shows a
row of portraits (`Renderer._draw_character_select_screen`); clicking one
or pressing Left/Right sets `Player.character_id`, and Enter/Space closes
the screen and starts play normally. `Player.character_id` is the only new
field on Player -- `Renderer` preloads every registered character's
animations up front (`assets.load_all_character_animations`) and looks up
the active one by id when drawing, so switching skins never needs to
reconstruct the Player.

## How the pause menu works

Esc opens a real menu instead of a plain "PAUSED" label, using
`assets/Menu/Buttons/Menu_jogo/`: **Resume** unpauses, **Restart** rebuilds
the whole run from the same seed (`GameApp.restart` -> `_new_run`, keeping
the chosen character skin), **Quit** exits, and **Settings** opens a small
sub-panel (`GameApp.settings_open`) with Zoom In/Out and Back -- reusing
the camera zoom that already existed rather than adding a fake "Settings"
button with nothing behind it. There's still no audio system (see
"Cross-cutting" in `TODO.md`), so Settings doesn't have a volume control.

## How Checkpoints work

A craftable, placeable tile (`tile_registry.CHECKPOINT_ID`). Touching one
(exact-tile overlap, the same check Spikes uses) makes it the player's new
respawn point and fires a Confetti burst -- both handled by
`game/world/checkpoints.py::try_activate`, kept out of `GameApp` so it's
unit-testable on its own, the same reasoning as `combat_system.py`.
Touching an already-active Checkpoint is a no-op (compares against
`Player.spawn_x/spawn_y`), so it doesn't re-burst confetti every frame you
stand on it. The active Checkpoint plays its "Flag Idle" animation; every
other one shows its plain "No Flag" texture -- there's no state stored per
tile for this, `Renderer` just compares each Checkpoint tile's position
against the player's current spawn point every frame.

## How the second-pass traps work (Fan, Sand/Mud/Ice, Falling Platform)

Three more `TileDef` opt-in fields, the same pattern as Spikes'
`contact_damage`/Trampoline's `bounce_velocity` (all default to
0/1.0/inert, so every existing tile is unaffected):

- **Fan** (`updraft_velocity`): non-solid. `Player._fan_updraft` scans the
  player's own column downward each frame for a Fan tile within
  `FAN_RANGE_TILES`, and if found overrides `y_vel` to a steady upward
  push (tapering to 0 at max range) instead of falling under gravity.
- **Sand/Mud/Ice** (`speed_multiplier`): solid variants of the ground you
  already mine (Sand/Mud blocks, Frozen Dirt for Ice).
  `Player._ground_speed_multiplier` reads the tile directly beneath the
  player's feet and scales that frame's horizontal move by it -- Sand/Mud
  slow you down, Ice speeds you up. Only applied while `on_ground`, so it
  never affects air control.
- **Falling Platform** (`CRUMBLE_PLATFORM_ID`, no new TileDef field --
  behavior lives in `World`, not the tile schema): solid until you stand
  on it continuously for `FALLING_PLATFORM_TRIGGER_S`
  (`World.notify_standing_on`, called from `Player.physics_step` while
  grounded), then it's replaced with air and scheduled to reform after
  `FALLING_PLATFORM_RESPAWN_S` (`World.update`). Leaving the tile (or
  never having stood on it) resets the timer -- `World` only tracks one
  "currently being stood on" position at a time, since there's one player.

## How the world-generated traps work (Spikes, Fire, Arrow Trap, Falling Platform, Fan, Sand/Mud/Ice)

All of the mechanical effects above are unchanged, but none of these seven
tiles is player-craftable/placeable any more (`TileDef.can_place=False`)
-- they're rolled during world generation, the same deterministic
"pure function of (seed, x)" approach as ore, trees and the moving hazard
anchors (see "Determinism" below), and the player just finds them while
exploring:

- **Static cave-floor hazards** (`world_generator._place_cave_hazard`,
  `CAVE_HAZARD_SPAWN_CHANCE_PER_COLUMN`): one roll per column picks at
  most one of Spikes/Fire/Arrow Trap/Falling Platform and places it at the
  first valid cave-floor spot below `CAVE_MIN_DEPTH_BELOW_SURFACE` -- an
  air tile with a solid floor beneath it and clear air above, i.e.
  somewhere the player can actually walk into and stand on. Shared across
  every biome, same as caves themselves.
- **Fan shafts** (`world_generator._place_fan_shaft`,
  `FAN_SHAFT_SPAWN_CHANCE_PER_COLUMN`, rarer than cave hazards): needs a
  taller find -- a floor with at least 4 clear tiles of air stacked above
  it (a small vertical shaft), so the updraft has room to actually push
  the player somewhere.
- **Biome surface traps** (`world_generator._surface_tile_for`,
  `SURFACE_TRAP_SPAWN_CHANCE_PER_COLUMN`): each biome's surface row is
  normally its plain ground tile, but a per-column roll occasionally swaps
  it for that biome's own surface trap instead -- Desert -> Loose Sand,
  Snow -> Slick Ice, Jungle -> Sticky Mud. Forest deliberately has no
  entry in this table (`_BIOME_SURFACE_TRAP_TILE`), so the world's fixed
  always-Forest spawn window stays hazard-free.

None of this is a separate subsystem from the mechanics above -- placement
is the only thing that changed; a Spikes tile found in a cave damages the
player exactly the same way a crafted one used to.

## How moving hazards work (Saw, Rock Head, Spike Head)

`game/world/hazard_feature.py`. Each is anchored to a fixed underground
position rolled deterministically at chunk-generation time
(`world_generator.generate_hazard_anchor`, called alongside tile/tree/ore
generation in `World.get_or_create_chunk`) -- a pure function of
`(seed, x)` that re-derives its own column to find a valid air pocket
under a solid ceiling, the same "any column works out its own content
independently" guarantee trees and ore already rely on. A `HazardAnchor`
stores only its spawn point and kind; its *current* position at any moment
is computed on the fly as a sine oscillation of `World.elapsed_s` (real
seconds since that `World` was created) -- there is no per-frame mutable
state to track, so a hazard does exactly the same thing whether its chunk
has been loaded continuously or just got regenerated after being unloaded.
`combat_system.resolve_hazard_feature_damage` damages and knocks back the
player on overlap, with the same invulnerability window as every other
contact-damage source.

This is a deliberate simplification of the source material: a "real" Rock
Head/Spike Head charges once triggered by the player getting close, which
would need per-hazard trigger/charge/return state colliding against the
static tile grid. These instead swing/thump on a fixed rhythm the player
has to time a pass around -- still a real hazard, just stateless.

## How particles work

`game/rendering/particles.py`: a small generic system (spawn, `update(dt)`
ages and removes expired ones, `Renderer._draw_particles` draws whatever's
left) for two short-lived cosmetic effects using real art from
`assets/Other/` -- footstep Dust while running on the ground, and a
one-shot Confetti burst when a Checkpoint activates (each spawned particle
picks a random frame from the 6-piece Confetti strip for color variety,
rather than re-tinting one frame at runtime). The player's ever-present
ground Shadow (also `assets/Other/`) is deliberately *not* part of this
system -- it isn't a short-lived effect, so it's drawn directly under the
player/enemies every frame instead of being spawned and expired.

## How equipment works

The inventory screen (`E`) is a two-panel "character sheet": a left column
with the player's portrait, one bordered slot per entry in
`game/inventory/equipment.py`'s `SLOTS` (currently Head and Body) and a
stats block (HP / total Defense / the selected hotbar item's Attack), and a
right-side bag grid (the same 20 inventory slots as before). Equipping
moves the item out of the bag into its slot (click an armor item in the
bag); unequipping moves it back (click the occupied slot). Every occupied
slot -- bag or equipment -- gets a border colored by `ItemDef.rarity`
(common/uncommon/rare/epic). `Equipment.total_defense()` sums every
equipped item's `defense` and is subtracted from incoming contact damage in
`combat_system.resolve_contact_damage`, floored at `MIN_DAMAGE_AFTER_DEFENSE`
so armor reduces damage but never fully negates it. The weapon slot in
combat is still the hotbar selection, not a separate equip slot -- see
"Controles" above.

## How to create a recipe

Add one `RecipeDef` entry in `game/crafting/recipe_registry.py`:
`ingredients` (a tuple of `(item_id, quantity)` pairs, all must already
exist in `item_registry.py`), `result_item_id`, `result_quantity`, and
`station_tile_id` (`None` for craftable-anywhere-by-hand, or a tile id like
`tile_registry.WORKBENCH_ID` to require the player stand within
`STATION_SEARCH_RADIUS_TILES` of that tile). No other file needs to change
-- the crafting screen (`C`) lists every registered recipe automatically,
grouped by the result item's category (see "How the crafting screen is
laid out" below), and scrolls (mouse wheel) once the list outgrows
`CRAFTING_VIEWPORT_HEIGHT` so the panel never grows into the HUD no matter
how many recipes get added later. It won't be craftable (or even show its
name) until the player has discovered every one of its ingredients -- see
"How recipe discovery works".

## How the crafting screen is laid out

A grid of icon cells on the left (several recipes side by side, not one
tall row each) plus a fixed details panel on the right for whichever cell
the mouse is currently over (`Renderer._draw_recipe_details`: name,
station badge, full ingredient list with live counts, and a status line --
"Click to craft", "Missing ingredients", "Needs Workbench nearby", or the
smelting-specific states below). The grid itself only needs to carry an
icon, a quantity badge and a thin colored border for status (green=ready,
grey=missing ingredients, amber=needs its station), since the actual
breakdown lives in the details panel -- hovering is what reveals it,
clicking is still what crafts it.

Cells are grouped by what the result item's `ItemCategory` *is*
(`_CATEGORY_SECTION_ORDER` in `renderer.py`: Building, Structures &
Utility, Tools, Weapons, Armor, Ammo, Materials) rather than by where
they're crafted -- a layout a player recognizes at a glance ("I want a
weapon" beats "I wonder which station this needs"); each cell's own
station requirement (`_station_label`: "Anywhere", "Workbench",
"Furnace", ...) shows up in the details panel instead. Smelt recipes (see
"How the furnace works") get their own trailing "Smelting" section, since
starting one is a different interaction (a timed job, not an instant
craft) even though the grid/details code is shared.

## How recipe discovery works

A recipe doesn't appear in the crafting screen **at all** until the player
has *discovered* every one of its ingredients -- obtained at least one,
ever (mined, looted from an enemy, crafted, or smelted), tracked
permanently in `Player.discovered_item_ids` (not cleared by death/respawn,
and not the same as *currently holding* the item -- you could discover
`wood`, spend it all, and the recipe stays unlocked).
`crafting_system.is_recipe_discovered` checks this, and `_recipe_sections`
filters undiscovered recipes out before the grid is even laid out -- a
category with nothing discovered in it doesn't show its header either.
This is deliberately an omission, not a "???" placeholder: with many
recipes registered, showing every locked one made the grid feel cluttered
and mysterious rather than inviting; discovering an item and then opening
the crafting screen to find a new option waiting is the intended "oh,
now I can make that" moment. `crafting_system.undiscovered_ingredients`
(what's still missing for one specific recipe) remains available for any
future UI that wants to hint at a "next" recipe -- just not surfaced in
the grid today.

Every place an item enters the player's possession routes through
`Player.collect_item` (mining drops in `InputHandler.update_continuous`,
enemy loot in `GameApp._collect_enemy_drops`, furnace output in
`GameApp._update_furnace`) or `crafting_system.craft_and_discover` (the
crafting screen's click handler, which also marks the *result* as
discovered on a successful craft -- crafting something for the first time
counts as having obtained it). Both helpers diff "which recipes were
discovered before" against "after" and return the newly-unlocked ones, so
`GameApp`/`InputHandler` can push a `"New recipe unlocked: X"` toast (see
"How on-screen notifications work") for each -- without a parallel
discovery-tracking system, this is the same registry scan both directions.

## How on-screen notifications work

`game/core/notifications.py`'s `NotificationQueue` is a small FIFO of
timed toasts drawn top-center (`Renderer._draw_notification`, a fading
box). Two things push to it: recipe-unlock announcements (see above,
`push`, one per newly-discovered recipe, furnace outputs ready) and the
specifically-requested blocked-mining message -- trying to mine a
tool-gated tile without the right tool now shows `"Requires a {Tool}"`
(`Player.blocked_mining_reason`, checked every frame the mine button is
held) instead of silently doing nothing. That one goes through
`push_throttled` (`NOTIFICATION_THROTTLE_S`) instead of plain `push`,
since holding the mouse button down would otherwise re-push the identical
message every single frame.

## How the furnace works

A craftable station (`tile_registry.FURNACE_ID`, `game/crafting/
furnace_system.py`) for turning ore into bars -- unlike everything else in
the crafting screen, smelting is a *started-then-collected* transaction,
not an instant one, because burning takes real time. Clicking a smelt
recipe (`SmeltRecipeDef`, `game/crafting/smelt_registry.py`) while
ingredients and a nearby furnace are available immediately consumes the
ore and fuel (Coal, for every current recipe) and starts a `FurnaceJob`
keyed by *that specific furnace tile's position* -- so multiple placed
furnaces can smelt in parallel, but each one only runs one job at a time
(a second click while busy just fails, shown in the UI as a dimmed
"Furnace busy with another bar" row for every *other* smelt recipe, and a
live progress bar for the one actually in progress). `GameApp` polls
`FurnaceManager.update(dt)` every frame; when a job's `smelt_time_s`
elapses it returns the finished `(item_id, quantity)` for `GameApp` to
grant via `collect_and_discover` (so a first Iron Bar can itself unlock
the Iron Pickaxe recipe) and announce with a "ready!" toast. Four ores
that were catalog-only in earlier phases now have a real obtain-then-use
path this way: Iron Ore, Topaz, Sapphire and Emerald each smelt into their
own Bar; only Iron Bar has a further crafting use so far (the Iron
Pickaxe) -- the other three remain catalog-only, same honest gap the raw
gems already had (see "Known limitations").

## How to create an enemy

Add one `EnemyDef` entry in `game/entities/enemy_registry.py`: `ai_type`
(`AIType.WALK` ground patrol/chase, `AIType.HOP` slime-style periodic
jumps, or `AIType.FLY` gravity-free hover/chase), `max_health`,
`contact_damage`, `move_speed` (px/tick -- see "Velocity units" above),
`width_tiles`/`height_tiles`, `color`, `spawn_weight` (relative chance
among all enemies when the spawner picks one), `spawn_time`
(`SpawnTime.ANY`/`DAY`/`NIGHT` -- gates which enemies `EnemySpawner` will
even consider based on `WorldClock.is_night`; Duskwing is `NIGHT`-only,
which is how "different enemies at night" is satisfied), `biome_id` (`None`
for any biome, or a `biome_registry` id like `DESERT_ID` to restrict it to
that biome -- Scorpion is desert-only, spawned by checking
`world_generator.biome_at` at the candidate spawn column), and optionally
`drop_item_id`/`drop_chance`/`drop_min`/`drop_max`. To add a genuinely new
*behavior* (not just new stats on an existing one), add a 4th `AIType` and
a matching `_update_*` function in `enemy_ai.py`.

There is no dedicated enemy art in `assets/` -- `assets/20 Enemies.png` is
only a promotional preview image for a separate paid pack (it has a
"download all 20 enemies, link in the project page" watermark baked in and
was never meant as usable game art), so it isn't used. Enemies are drawn as
flat colored shapes by `ai_type` in `renderer.py`'s `_draw_enemies` (ellipse
for HOP, diamond for FLY, rectangle for WALK) until real sprites are added.

## How biomes work

The world is split into fixed-width horizontal zones
(`BIOME_ZONE_WIDTH_TILES`). `world_generator.biome_at(seed, x)` is a pure
function of `(seed, x)`: within half a zone-width of the world's exact
center it's always Forest (a fixed-radius safety window, not just "whichever
zone the center happens to land in" -- see the docstring for why that
distinction matters), and every other zone independently rolls a biome
weighted by `BiomeDef.zone_weight`. `generate_column` looks up the biome for
its own column and uses its `surface_tile_id`/`subsurface_tile_id` instead
of a hardcoded grass/dirt. The deep underground is biome-specific too:
below the dirt/subsurface layer, `_ore_at` fills stone with that biome's own
`underground_tile_id` (Forest keeps plain Stone; Desert/Snow/Jungle get
Desert Stone/Permafrost Stone/Jungle Stone) and gives a small extra roll
(`exclusive_ore_tile_id` / `exclusive_ore_chance`) at a biome-exclusive gem
-- Topaz in Desert, Sapphire in Snow, Emerald in Jungle -- stacked on top of
the universal Coal/Iron roll that exists under every biome. Caves are the
one thing that stay identical everywhere: the same noise field decides
"air pocket or not" regardless of which biome's stone it would otherwise
carve out of. Vegetation is biome-aware too: Desert suppresses the normal
tree roll and grows cacti (1-2 tiles tall, single column) instead; Forest,
Snow and Jungle all currently share the same tree system unchanged. "Cave"
is a fifth biome only in the sense that it was already built in Phase 1
(universal underground cave generation, independent of the surface biome
above it) -- it never needed its own zoning since it isn't a horizontal
region.

## How to create a biome

Add one `BiomeDef` entry in `game/world/biome_registry.py`:
`surface_tile_id`/`subsurface_tile_id`/`underground_tile_id` (existing or
new `TileDef`s -- see "How to add a new tile") and `zone_weight` (relative
chance among non-Forest zones). That alone makes it generate with its own
deep stone, the universal coal/iron finds, and the default tree vegetation.
Add `exclusive_ore_tile_id`/`exclusive_ore_chance` for a biome-exclusive
ore (see Topaz/Sapphire/Emerald as worked examples in `tile_registry.py`,
`item_registry.py` and `biome_registry.py`). For unique surface
vegetation/decoration or a biome-exclusive enemy, see
`_place_desert_decoration` in `world_generator.py` and the
`EnemyDef.biome_id` field, respectively.

## How to create an NPC

Not implemented yet — this is Phase 8. See `TODO.md`. Documenting "how to
add one" here before the system exists would describe something that
doesn't exist yet, so it's deferred until that phase lands.

## How procedural structures work

Three kinds -- House, Ruins, Underground Room -- generated by
`game/world/structures.py`, the same "pure function of (seed, x)"
determinism as everything else in world generation. Placement uses a
coarse slot grid (`STRUCTURE_SLOT_WIDTH_TILES`) and mirrors the tree-slot
pattern exactly (`world_generator._tree_center_for_slot`/`_tree_role_at`):
one deterministic roll per slot decides whether it has a structure, which
kind, and its anchor position, independent of which column is asking --
required so any column can re-derive the same answer regardless of chunk
load order.

Each structure is a hand-built 7-wide blueprint: a `dx -> {dy: tile_id}`
dict relative to an anchor row.

- **House** (surface, common): Wood Plank floor/walls/roof, a 3-tile
  interior, a doorway, a Torch, a Chest, and a Workbench.
- **Ruins** (surface): the same footprint in Stone, no roof, and each wall
  tile independently has `RUINS_WALL_COLLAPSE_CHANCE` of being left out of
  the blueprint entirely -- unlike every other cell, a collapsed wall tile
  is deliberately *not* forced to air, so whatever's naturally there (a
  tree branch, bare sky) shows through the gap, reading as
  reclaimed-by-nature decay. The floor, interior walking space, and Chest
  are always guaranteed clear regardless.
- **Underground Room**: forcibly carved out of rock at
  `UNDERGROUND_ROOM_MIN_DEPTH_BELOW_SURFACE`+ tiles deep, regardless of
  what was there (solid stone, ore, natural cave air) -- walls/ceiling use
  that column's own biome `underground_tile_id` (a Desert room reads as
  Desert Stone, not generic Stone), a Wood Plank floor, a Torch, a Chest.
  Force-carving instead of finding an existing pocket (unlike the moving
  hazards) is a deliberate simplification that keeps it a pure function of
  seed alone. Finding one in the dark, torch-lit, is the payoff for the
  underground-darkness system (see "How the day/night cycle and lighting
  work").

A House/Ruins placement is skipped (rerolls to nothing) if the surface
height varies more than `STRUCTURE_MAX_TERRAIN_VARIANCE_TILES` across its
footprint, so nothing visibly floats over a cliff or gap --
`structures.place_structures` runs last in `generate_column` (after cave
hazards/fan shafts), so a structure's carve/overwrite always wins over
whatever natural terrain/hazard would otherwise be there, same
last-applied-wins layering already used for decoration -> hazards -> fan
shafts. `STRUCTURE_MARGIN_TILES` keeps neighboring slots' footprints from
ever overlapping.

The Chest (`tile_registry.CHEST_ID`) isn't player-craftable/placeable,
only found inside structures -- it reuses the existing `drop_pool`
mechanism (the same "one of several possible drops" Berry Bush already
uses) for its loot, drawing from already-registered valuable items
(`iron_bar`, `topaz`, `sapphire`, `emerald`, `iron_pickaxe`, `wood_sword`,
`wood_helmet`) rather than a whole new loot-table system. Its texture
reuses `assets/Items/Boxes/Box2` -- the same pack as the wooden crate
(Box1), previously unused.

**Tower is deliberately not implemented**: the game has no
ladder/climbing mechanic (only single + double jump), so a tall vertical
structure's loot would be unreachable without one.

## How save/load works

`game/core/save_system.py`: `serialize`/`deserialize` are pure functions
(no file I/O, independently testable), with thin `save_to_file`/
`load_from_file`/`save_exists` wrappers around a single save slot
(`SAVE_FILE_PATH` = `saves/save.json`, gitignored).

What's persisted: the world seed, `world.elapsed_s` (so the moving
hazards' oscillation stays continuous), the world clock (time of day, day
count), full player state (position, spawn point, character skin,
health, inventory, equipment, `discovered_item_ids`), and any in-progress
Furnace jobs. **Only modified chunks are saved, and only their changed
tiles** -- `Chunk.dirty` already existed for exactly this (set the moment
any tile is mutated); at save time each dirty chunk's live tiles are
diffed column-by-column against a freshly recomputed procedural baseline
(`generate_column(seed, x)` -- a cheap pure function, the same cost
already paid every chunk load/unload) and only the `(local_x, y, tile_id)`
triples that actually differ are written out. Loading replays those diffs
on top of ordinary procedural generation, so an unmodified chunk needs no
saved data at all.

Not persisted (transient/regenerable, same as what already happens after
Restart): enemies, projectiles, particles, on-screen notifications. No
NPCs exist yet to persist either.

Two pause-menu buttons, Save and Load (`GameApp.save_game`/`load_game`),
wired through `InputHandler._handle_pause_click` exactly like the
existing Restart button. Save writes the file and pushes a "Game saved"
toast; Load reads it (a "No save found" toast and a no-op if the file
doesn't exist) and rebuilds `world`/`player`/`world_clock`/
`furnace_manager` from the deserialized data, resetting the same per-run
transient state `_new_run` already resets on Restart. No Save/Load art
exists in `assets/Menu/Buttons/Menu_jogo/`, so their icons are hand-drawn
(a floppy disk, a down-arrow into a tray) -- same precedent as the
tool/weapon icons.

## Known limitations

- Save is single-slot (`saves/save.json`) -- no multiple save files or a
  picker UI. Enemies, projectiles, particles, and on-screen notifications
  aren't persisted (see "How save/load works").
- No NPCs or bosses yet (see `TODO.md`).
- Biomes have hard borders (no blending/transition strip between zones);
  caves are identical in every biome (same noise field regardless of the
  biome's stone); only Desert has unique surface vegetation (cacti) and an
  exclusive enemy (Scorpion) -- Snow and Jungle currently reuse Forest's
  tree system and have no exclusive enemy of their own yet (see "How biomes
  work"). Underground stone and gem ores (Topaz/Sapphire/Emerald) *are*
  biome-specific, and each is now smeltable into its own Bar at a Furnace
  (see "How the furnace works") -- though none of the three Bars has a
  further crafting use yet, same gap `iron_ore` used to have.
- Lighting doesn't respect occlusion -- a torch shines through thin walls
  with a plain distance falloff rather than stopping at solid tiles (see
  "How the day/night cycle and lighting work").
- Only 1 light source exists (Torch); only 1 enemy (Duskwing) is
  night-exclusive -- the other two spawn at any time of day.
- Only 4 enemies (slime, crawler, duskwing, scorpion), all flat-colored
  shapes -- no dedicated enemy art exists in this repo (see "How to create
  an enemy").
- Enemy kills grant loot directly to the player's inventory; there's no
  physical "item drop on the ground to walk over" entity yet.
- Armor has exactly 2 equip slots (Head, Body).
- A furnace smelts one job at a time with no queue (placing more furnaces
  is the way to parallelize); Coal is the only fuel, one fixed quantity
  per recipe, no fuel-efficiency mechanic.
- Topaz/Sapphire/Emerald Bars are smeltable but still have no further
  crafting use (same gap Iron Bar would have had without the Iron
  Pickaxe) -- no tool/weapon/armor tier exists for them yet.
- Only one tile can grant a random drop (Berry Bush, via `TileDef.drop_pool`)
  -- every other tile still has exactly one fixed `drop_item_id`.
- Inventory/crafting UIs are click-driven panels (equip, unequip, craft,
  scroll), not full drag-and-drop or animated interfaces.
- The pause menu's Settings only has Zoom (the one thing already fully
  working) -- no audio controls, since there's still no audio system, and
  no world-select screen.
- Saw/Rock Head/Spike Head swing on a fixed rhythm (a sine oscillation of
  elapsed time) rather than charging when the player gets close -- see
  "How moving hazards work" for why.
- The Sand/Mud/Ice traps reuse the same tinted-base-tile technique as the
  biome ground tiles they resemble, rather than slicing
  `assets/Traps/Sand Mud Ice (16x6).png`, whose cell layout isn't
  documented anywhere in the pack.
- Only 4 playable character skins exist (all from the same asset pack,
  same stats/hitbox) -- picking one is purely cosmetic.
- Only grass/dirt/stone/crate/chest/spikes/trampoline/the fruits have
  dedicated source art; everything else (ore, bedrock, workbench, tree
  trunk/leaves, planks, biome tiles/gems) is a tinted grass/dirt/stone
  sprite with a small procedural detail layered on top (see "Art reuse"
  above) until dedicated art exists. Tool/weapon/armor icons, the Berry
  Bush, and the Save/Load pause-menu icons are hand-drawn vector shapes
  for the same reason -- this asset pack has no matching art for those.
- No auto-tiling: every tile of a given type looks identical regardless of
  its neighbors (no smooth edge/corner blending yet).
- Trees are a single trunk column with a small 3-wide canopy, not the full
  varied-shape forests of Phase 6 biomes.
