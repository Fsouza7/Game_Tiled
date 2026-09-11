# Sandbox Prototype

A 2D sandbox exploration/mining/building game, built incrementally in
phases. Inspired by the genre popularized by Terraria/Starbound/Minecraft,
with an original tile set, world generator and code base -- no third-party
game code, names or maps are reused. Real sprite art from the bundled
`assets/` pack *is* reused for visuals (tiles, player, items -- see "Art
reuse" below); none of it drives gameplay data, and every reuse is
documented rather than pretended away.

> **Status: Phase 8 (NPCs) + Phase 7 (structures + save/load) + Summoner
> class + RPG skill/leveling system** — see `TODO.md` for the full
> roadmap and what is/isn't implemented yet.

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
case, and the furnace's start/busy/complete/restart smelt-job lifecycle),
the Summoner class (class/summon registry sanity, the weapon_class
gate blocking attacks both ways, casting-then-replacing a summon through
the real input path, a summon chasing/damaging a nearby enemy and hovering
near the player otherwise, the class-select screen's click+confirm path,
and a full app boot through both select screens), the skill/leveling
system (the XP curve against known reference values, level-up queuing,
skill-tree gating, every multiplier/bonus helper, every XP hook point
across combat/mining/crafting, the Magic-boosted summon damage, the
crafting material-refund roll, and a full app test driving real level-up
notifications and the Skills screen's click-to-select/unlock flow), and
Phase 8 NPCs (registry/shop-price sanity, spawn conditions for Guide/
Merchant/Blacksmith, house-or-fallback home assignment, dialogue wrap,
buy/sell including the inventory-full refund and the can't-sell-coins
guard, T-to-talk plus shop click-to-buy/sell through the real
InputHandler, and a full GameApp path that spawns the Guide, talks to
them, then unlocks the other two and round-trips them through save/load
without re-announcing).

## Controls

A title screen appears at startup: Continue (if a save exists) or New
Game. New Game then shows character select (click a portrait or Left/Right,
Enter/Space to confirm) and class select immediately after (same
click/arrow-keys/Enter controls, text cards instead of portraits) -- see
"How the title screen works" and "How the Summoner class works" below.
Continue loads the save and skips both. Everything below applies once
you're in the world.

| Action | Default key |
|---|---|
| Move left/right | A/D (arrow keys still work if they aren't rebound to something else) |
| Jump (press again mid-air for a double jump) | Space |
| Mine / break block | Left mouse (hold) |
| Place block | Right mouse |
| Select hotbar slot | 1-9 |
| Eat the selected food item (heals HP) | F |
| Summon the Slime King boss (needs a Slime Core Idol selected) | G |
| Zoom in/out | Mouse wheel, or +/- |
| Open/close inventory & equipment | I |
| Equip an armor piece (while inventory is open) | Left-click it in the bag |
| Unequip an armor piece (while inventory is open) | Left-click its equipment slot |
| Show an item's tooltip (name, description, stats -- while inventory is open) | Hover it |
| Equip an armor piece, or send any other item to the selected hotbar slot (while inventory is open) | Right-click it in the bag |
| Open/close crafting | C |
| Craft a recipe / start a smelt job (while crafting is open) | Left-click its row |
| Scroll the crafting list (while crafting is open) | Mouse wheel |
| Open/close Skills (levels + skill-point tree) | K |
| Talk to a nearby NPC, open a Chest, toggle a Door, or sleep in a Bed | T |
| Use equipped accessory (Grapple Hook) | E |
| Open/close Map | M |
| Select a skill / unlock an eligible tree node (while Skills is open) | Left-click it |
| Attack (melee or ranged -- select a weapon in the hotbar first) | Left-click |
| Pause (opens a real menu: Resume/Settings/Save/Load/Restart/Quit) | Esc |
| Rebind a gameplay key | Esc -> Settings, click the key, press a new one |
| Debug overlay (FPS, pos, chunk, seed, enemy count, day/time/ambient) | F3 |
| Toggle debug mode (see "How the debug tools work") | F4 |
| Debug: unlock all recipes / reveal map / full heal + coins / spawn all bosses / spawn all enemies / teleport to cursor / teleport to spawn (debug mode only) | F5 / F6 / F7 / F8 / F9 / F10 / F11 |

Combat: with any weapon selected, the character continuously faces the
mouse cursor (a small crosshair reticle marks the aim point -- yellow for
melee, red for ranged) so the swing/shot direction is never a surprise.
With a melee weapon (Wood Sword) selected, left-click swings in a
`MELEE_ARC_DEGREES`-wide cone centered on the cursor -- it hits whatever
the mouse points at, not just strictly left/right -- and plays a brief
slash-arc visual in that direction. With a ranged weapon (Wood Bow)
selected and arrows in your inventory, left-click fires an arrow straight
at the cursor. Hits show a floating damage number at the point of impact
(red when you take damage, gold when an enemy does). Left-click only
mines/attacks -- whichever the selected item supports -- so mining is
automatically disabled while a weapon is selected.

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
    equipment.py         # RPG-style armor slots (head/body/legs/boots/accessory): equip/unequip, total defense
  crafting/
    recipe.py           # RecipeDef schema (ingredients, result, optional station)
    recipe_registry.py   # every recipe, one entry each (add recipes here)
    crafting_system.py   # ingredient/station checks, the craft transaction, and recipe-discovery logic (no UI code)
    smelt_recipe.py       # SmeltRecipeDef schema (ore+fuel -> bar, over time)
    smelt_registry.py      # every smelt recipe, one entry each (add ore->bar pairs here)
    furnace_system.py       # FurnaceManager: per-furnace input hopper (fuel+ore) + timed smelt jobs that auto-restart into a queue
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
  npcs/
    npc_def.py            # NpcDef + ShopOffer schema
    npc_registry.py        # Guide, Merchant, Blacksmith (add NPCs here)
    npc.py                 # runtime NPC instance (position, dialogue cursor)
    npc_spawner.py          # spawn conditions + house/fallback home assignment
    shop.py                 # buy/sell transactions (coins), inventory wealth
  core/
    camera.py           # smooth follow + world-bound clamping + zoom
    debug_overlay.py     # F3 HUD
    world_clock.py        # day/night timekeeper; derives the ambient light curve
    notifications.py      # small FIFO toast queue (recipe unlocks, blocked-mining messages)
    game_app.py          # the game loop; wires world/player/camera/input/renderer together
  input/
    bindings.py          # rebindable gameplay keys + defaults/reserved list
    input_handler.py    # keyboard/mouse -> game actions (reads GameApp.prefs.bindings)
  rendering/
    renderer.py          # draws world/player/HUD/inventory+equipment panel/crafting panel; no gameplay logic
    assets.py            # loads/slices real art and builds procedural textures+icons
    particles.py          # Dust/Confetti: a small generic spawn/update/expire particle system
    damage_numbers.py     # floating "-N" pops at hit position (player red, enemy gold)
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
- **Art reuse**: `GRASS_ID`/`DIRT_ID` are sliced from a user-supplied
  `assets/Tiles/Tileset Outside.png` and `STONE_ID` from `Tileset Inside.png`
  (32px autotile-style sheets; only one representative cell per tile id is
  used, not the full neighbor-aware autotiling both sheets have the pieces
  for -- see `_OUTSIDE_TILESET_CELLS`/`_INSIDE_TILESET_CELLS` in
  `game/rendering/assets.py`), and the player uses the
  `assets/MainCharacters/NinjaFrog` sprite sheets. Everything else (ore,
  bedrock, workbench, the legacy tree trunk/leaves, planks, every biome's
  ground/deep-stone variant) reuses the closest base sprite (grass/dirt/
  stone) with a color tint *plus* a small procedural detail -- speckles for
  ore, bark/plank lines, a tabletop band for the workbench -- so it reads as
  a distinct material instead of a flat color wash. A tile with no mapped
  texture at all falls back to its `TileDef.color` as a flat rectangle. The
  same idea applies to
  item icons: a block icon reuses its tile's texture
  (`ItemDef.places_tile_id`/`icon_tile_id`). A user-supplied icon sheet
  (`assets/Items/#2 - Transparent Icons & Drop Shadow.png`, ~350 hand-drawn
  fantasy RPG icons on a 16-col x 32px-cell grid, `game/rendering/assets.py`)
  now covers nearly every item that isn't a placeable block: direct crops
  for single-icon matches (`_SHEET_ICON_CELLS` -- Wood Sword, Wood Bow,
  Grapple Hook, Slime Gel, Feather, Coin, the five ore items, and three
  boss items -- Slime Core Idol/Slime King's Core/Crown -- that previously
  had no icon at all), plus a `_colorize(base, color)` helper (recolors a
  real icon by its own luminosity, not a flat alpha wash, so it keeps its
  shading) that turns one real shape into several tinted tiers: the 5
  pickaxes, the 6 bars, 13 armor pieces across wood/iron/steel + a
  standalone Arcane Helm, both summon rods, and the Arcane Staff (see
  `_PICKAXE_BASE_CELL`/`_INGOT_BASE_CELL`/`_ARMOR_BASE_CELLS`/
  `_CROWN_BASE_CELL`). Only the Arrow icon is still a hand-drawn vector
  shape (`_build_procedural_icons`) -- no matching ammo art exists in the
  sheet. Placeable blocks/decorations and the 8 fruit items (dedicated real
  sprites) were deliberately left alone.

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
  `SLOTS`, currently `"head"`/`"body"`/`"legs"`/`"boots"`) and `defense` (flat damage
  reduction applied in `combat_system.resolve_contact_damage`). Accessories
  use `"accessory"`. Add a new body-part slot by adding its name to `SLOTS`;
  the inventory screen lays out one box per slot automatically.
- **Icon**: resolution order is `places_tile_id` (block/decoration -- uses
  the tile's own texture) -> `icon_tile_id` (borrow any tile's texture
  without being placeable, e.g. an ore or raw material) -> `icon_key`
  (looked up in `game/rendering/assets.py`: a real sprite added to
  `_STATIC_ICON_SOURCES`, a cell from the user-supplied icon sheet added to
  `_SHEET_ICON_CELLS` (or, for a tiered item, a base cell + `_colorize` tint
  added to one of the `_PICKAXE_BASE_CELL`/`_INGOT_BASE_CELL`/
  `_ARMOR_BASE_CELLS`-style tables), or a hand-drawn vector icon added to
  `_build_procedural_icons` -- the sheet wins over a vector icon registered
  under the same key) -> a flat color swatch by category as the last
  resort. Prefer `icon_tile_id` over a flat swatch whenever the item
  corresponds to an existing tile, unless a clean single-icon match already
  exists in the sheet (see the ore items, which now prefer that over their
  own tile's texture). Before adding a new sheet cell, zoom in on a
  column-labeled crop of the sheet first -- two cells were mis-picked from
  the thumbnail early on (a plain wooden staff looked like a hook at a
  glance) and had to be corrected once rendered at real size.

## How trees work

Trees are generated the same deterministic way as everything else: the
world is divided into fixed-width slots (`TREE_SLOT_WIDTH`), and each slot
independently rolls whether it contains one tree and at which column
(`TREE_SPAWN_CHANCE_PER_SLOT`, in `world_generator.py`). This keeps the
"any column can be generated independently, in any order" guarantee: a
column figures out whether it's a tree's own column, or just within a
nearby tree's footprint, purely by re-deriving its slot's roll
(`_nearest_tree_center`), without needing neighboring columns to already
exist.

A tree is a **single tile** (`TREE_ID`, placed at the trunk's base) that
renders as a real sprite from a user-supplied `assets/Tiles/Trees.png` (two
64x96 variants, picked by a deterministic hash of the tile's own column) --
not the stacked trunk+canopy tile blocks this game originally shipped with.
`Renderer._draw_world` special-cases `TREE_ID`: it collects every tree tile
seen during the normal per-tile pass and draws their sprites in a second
pass afterward, anchored bottom-center on their one tile but spanning 2
tiles wide x 3 tiles tall -- doing it as a second pass (rather than inline,
like every other tile) means a tree's overlap into a neighboring column
never gets painted back over by that column's own (later-drawn) ground
tile. `TREE_ID` is `solid=False`, same as the tile system it replaced, so
it doesn't block movement (user feedback: a tree shouldn't be able to
block a chase) -- and since it only ever sits *above* the ground column it
grows from, that doesn't touch the walkable surface tile underneath either.

**Chopping fells the whole tree at once** (user-requested: "faça um
sistema diferente pra cortar ela, pra ela cair de uma vez"), simply because
there's only one tile to break now instead of five (3 trunk + 2 leaf tiles
the old system chopped separately). `TileDef.break_quantity` (default 1,
every other tile) is 5 for `TREE_ID`, so that one break still grants a
whole tree's worth of `wood` -- the same total the old 5-tile version gave,
just in one drop instead of five (`InputHandler.update_continuous` reads
`break_quantity` off the tile id *before* `Player.try_mine` breaks it, and
adds it on top of the usual fortune-chance +1 bonus). The trade-off:
clicking to chop now has to land on the tree's one actual tile (the trunk's
base), not anywhere on the wider visual canopy -- the same tradeoff games
like Terraria make for the same reason.

`TREE_TRUNK_ID`/`TREE_LEAVES_ID`, the old tile ids, are still registered
(with their original tinted-dirt/grass textures) purely so an existing
save's chunk diff can still resolve a leftover one without a `KeyError` --
world generation just never places them anymore.

## How the parallax background works

A user-supplied 4-layer pack (`assets/Backgrounds/`: Sky, Clouds, Rock
Mountains, Grass Mountains, each a 320x320 PNG) replaced the single flat
tiled color swatch this game started with. `Renderer._draw_background`
draws them back to front, each scrolling horizontally at its own speed
(`settings.BACKGROUND_LAYER_PARALLAX`: 0.0 for Sky up to 0.45 for Grass
Mountains, the nearest/fastest layer) for a depth cue -- Sky is opaque and
covers the whole canvas; the other three have a transparent top half and an
opaque silhouette along the bottom (clouds / distant rock peaks / nearer
grassy peaks), each pre-scaled once (in `Renderer.__init__`, not per frame)
to the window's own height. Only the horizontal axis tiles/scrolls: each
layer is a fixed sky+skyline composition, not a repeating ground texture,
so tiling vertically would incorrectly stack mountain silhouettes on top of
each other going up into open sky. All four images are pixel-identical at
their left and right edges, so horizontal tiling has no visible seam.

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

## How enemy spawn density works

`EnemySpawner._current_limits` (`game/entities/enemy_spawner.py`) picks a
population cap and spawn cadence from *where and when* the player
currently is, instead of one fixed value for the whole game:

| Situation | Max alive | Spawn interval |
|---|---|---|
| Surface, day | `ENEMY_MAX_ALIVE_DAY` (5) | `ENEMY_SPAWN_INTERVAL_DAY_S` (5s) |
| Surface, night | `ENEMY_MAX_ALIVE_NIGHT` (10) | `ENEMY_SPAWN_INTERVAL_NIGHT_S` (3s) |
| Underground (any hour) | `ENEMY_MAX_ALIVE_UNDERGROUND` (14) | `ENEMY_SPAWN_INTERVAL_UNDERGROUND_S` (2s) |

"Underground" triggers once the player is `UNDERGROUND_SPAWN_DEPTH_TILES`
(4) below `World.surface_height_at(x)` -- a few tiles of slack so a
shallow dip in the terrain doesn't flicker the state -- and **overrides
day/night entirely**: caves are already dark regardless of the surface
cycle (see "How the day/night cycle and lighting work" above), so they're
dangerous at any hour, not just at night.

Enemies previously only ever spawned at the world surface, no matter how
deep the player actually was. `_underground_spawn_y_tiles` closes that
gap: it scans vertically near the player's own depth in a random nearby
column for a real cave spot (a solid floor under open air for ground
mobs; a flyer just needs one open tile, since it ignores gravity/collision
entirely -- see `enemy_ai._update_fly`) and simply skips that spawn
attempt if nothing suitable turns up, rather than silently falling back
to the surface. The enemy *roster* itself is unchanged -- the same
biome-weighted picks as the surface (Scorpion still desert-only) show up
underground too, just more often and at any hour.

## How day-based enemy difficulty scaling works

The world gets more dangerous the longer a playthrough runs (user
request: "cada dia que passa os mobs ficam mais fortes"). `game/entities/
difficulty.py`'s `health_multiplier(day_count)`/`damage_multiplier
(day_count)` are pure functions of `WorldClock.day_count` -- day 1 is
always the unscaled 1.0x baseline; each day after that adds
`ENEMY_HEALTH_PCT_PER_DAY` (8%) / `ENEMY_DAMAGE_PCT_PER_DAY` (5%), capped
at `ENEMY_DIFFICULTY_MAX_DAY` (30) so a very long playthrough doesn't
scale into absurd numbers (by day 30: +232% health, +145% damage, then
flat).

The multiplier is baked into an `Enemy`/`Boss` instance **at spawn time
only** (`health_multiplier`/`damage_multiplier` params on
`Enemy.__init__`, both defaulting to 1.0 so every pre-existing call site
is unaffected) -- it's never retroactive, so a Slime that's been alive
since day 1 doesn't suddenly get tougher when day 10 arrives; only mobs
spawned *after* that point do. This is also why `Enemy` now keeps its
own `max_health`/`contact_damage`, separate from the shared, frozen
`EnemyDef` it points to -- two Slimes spawned on different days can
genuinely differ in toughness without the definition itself ever being
mutated. `EnemySpawner._try_spawn` (called every regular spawn),
`GameApp.try_summon_boss`, and the F8/F9 debug spawn tools all read
`self.world_clock.day_count` and pass the resulting multipliers through.
The Slime King's enrage-minions inherit the boss's own already-scaled
stats (`boss.max_health / boss.enemy_def.max_health`) rather than
needing `day_count` threaded down into `boss_ai.py` separately.

## How the always-on enemy name + HP bar works

Every alive non-boss enemy now shows its name and a small HP bar
floating just above it, all the time -- not just once damaged (user
request: "coloque para mostrar a vida deles e o nome em cima do
sprite"). `Renderer._draw_entity_health_bar` is called for every enemy
regardless of whether it renders as a real sprite (`enemy_animations`)
or a flat vector shape (Slime's ellipse, Duskwing's diamond, ...) --
previously this only fired for sprited enemies, and only while
`health < max_health`, so a flat-shape mob (or any full-health one) had
no name or bar at all. Bosses are explicitly skipped here (an
`ai_type == AIType.BOSS` early-return) since they already get a
persistent top-center name+phase+bar (`_draw_boss_bar`, drawn once per
frame regardless of hover/proximity) -- a second one floating over the
sprite would just be redundant.

## How the Building system works (Doors, Beds & Sleeping)

Houses need no new tile type for their walls -- the existing placeable
Wood Plank/Stone Blocks already work, and the shelter check below only
cares about solidity, not tile type. Two new tiles complete the loop:

**Door** (`tile_registry.DOOR_CLOSED_ID`/`DOOR_OPEN_ID`, a Workbench
recipe: 6 Wood). Press **T** near one to toggle it between solid (closed)
and passable (open) -- `game/world/doors.py`'s `toggle`, using
`World.set_tile` (a new generic public method) to swap the actual stored
tile id, the same trick Falling Platform already uses for its
crumble/respawn transition, just player-driven instead of timer-driven.
Breaking either state still drops the same item, so opening a door never
costs you the ability to pick it back up.

**Bed** (`tile_registry.BED_ID`, a Workbench recipe: 8 Wood + 4 Wood
Plank). Press T near one to sleep and skip straight to morning
(`WorldClock.skip_to_morning`, always moving forward in time -- to
tomorrow's dawn if it's already past today's, or later today otherwise),
but only **at night**, and only inside a real **enclosed shelter**.
`beds.try_sleep` returns a human-readable reason on failure (same shape
as `Player.blocked_mining_reason`) for `InputHandler` to surface as a
notification.

Shelter detection (`game/world/shelter.py`) is a bounded flood-fill (BFS)
from the bed's own tile through every reachable non-solid tile:
- Exhausts within `SHELTER_MAX_AIR_TILES` (200, roughly a 14x14 open
  interior) -> a real, bounded room -> sleep allowed.
- Still has tiles left to visit when the cap hits -> the space leaks into
  the open world (or is simply too big to read as a cozy room) -> sleep
  refused ("This isn't a safe, enclosed shelter").

A successful sleep triggers a brief black-screen fade-out
(`GameApp.sleep_fade_remaining_s`/`SLEEP_FADE_DURATION_S`,
`Renderer._draw_sleep_fade`, drawn over everything including the pause
overlay) so an instant clock jump reads as a night passing, not a glitch
-- plus a new soft descending `sleep` sfx (the mirror image of
`level_up`'s ascending chime) and a "Slept through the night" toast.

Known gaps: no dedicated Door/Bed art (a flat `TileDef.color` swatch,
same fallback most newer tiles already use -- see
`Renderer._tile_texture`); doors don't auto-close, animate, or affect
enemy pathing (enemies don't path around obstacles at all currently); a
Bed only skips time, it doesn't also become a respawn point (still
Checkpoint's job); sleeping doesn't clear or otherwise reset nearby
danger -- whatever was already spawned stays exactly where it was.

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

## How the title screen works

On boot, `GameApp.title_open` blocks the game loop and shows Continue /
New Game (`Renderer._draw_title_screen`) instead of jumping straight into
character select. Continue is disabled until a save exists
(`save_system.save_exists`); clicking it (or pressing Enter when a save
is present) calls `GameApp.load_game` and skips character/class select.
New Game (or Enter with no save) closes the title and opens character
select as before. Single-slot save (`saves/save.json`), same file the
pause menu already uses.

## How character select works

`assets/MainCharacters/` has 4 interchangeable skins (Ninja Frog plus Mask
Dude/Pink Man/Virtual Guy) with identical frame sizes and animation
filenames, registered in `game/entities/character_registry.py`. After New
Game on the title screen, `GameApp.character_select_open` blocks the
normal game loop and shows a
row of portraits (`Renderer._draw_character_select_screen`); clicking one
or pressing Left/Right sets `Player.character_id`, and Enter/Space closes
the screen and opens class select. `Player.character_id` is the only new
field on Player -- `Renderer` preloads every registered character's
animations up front (`assets.load_all_character_animations`) and looks up
the active one by id when drawing, so switching skins never needs to
reconstruct the Player.

## How the pause menu works

Esc opens a real menu instead of a plain "PAUSED" label, using the UI
reskin's wood-plank buttons (see "How the UI theme works"): **Resume**
unpauses, **Restart** rebuilds the whole run from the same seed
(`GameApp.restart` -> `_new_run`, keeping the chosen character skin),
**Quit** exits, and **Settings** opens a real panel
(`GameApp.settings_open`, see "How the Settings screen works") with Zoom,
Music Volume and SFX Volume steppers, a click-to-rebind Controls grid, plus Back.

## How the Settings screen works

A proper panel (`Renderer._draw_settings_panel`, reusing the UI reskin's
`_draw_panel_chrome`) instead of the original 3 bare buttons floating on
the pause overlay: one row per adjustable value --
**Zoom** (the pre-existing camera control), **Music Volume**, **SFX
Volume** -- each a `-`/`+` stepper (`VOLUME_STEP` per click) around a
live percentage, then a two-column **Controls** grid of every rebindable
gameplay key (`game/input/bindings.py`), plus **Reset Keys** and **Back**.

Click a key chip to listen; the next keypress assigns it (swapping with
whoever already owned that key, so two actions never share one). Esc
cancels a listen without closing Settings. Esc, Enter, 1-9 and F1-F12
are reserved -- binding them would brick pause, the hotbar, or debug --
and mouse / zoom +/- stay hardcoded. Arrow keys still move left/right
unless that arrow is already somebody's binding. Bindings live on
`GameApp.prefs.bindings` and persist to `saves/settings.json` next to
volume, so Restart/Load never reset them. An old settings file with no
`bindings` field just gets the defaults.

Music/SFX volume are held on `GameApp.prefs`
(`game/core/settings_store.py`'s `Settings`), loaded once in
`GameApp.__init__` -- deliberately *not* in `_new_run`, since preferences
aren't part of "one playthrough": Restart and Load must never reset how
loud the player set things, unlike `world`/`player`/everything else that
gets rebuilt there. Preferences persist to `saves/settings.json`
(separate from the save slot itself) via `GameApp.adjust_music_volume`/
`adjust_sfx_volume`, which clamp to 0-1, apply immediately
(`pygame.mixer.music.set_volume` / a new `sfx.set_volume` -- a master
gain applied per-`Sound` at `play()` time, not baked into the cached
waveform bytes, so it takes effect without re-synthesizing anything) and
save on every click, and write to disk on every adjustment. A missing or
corrupt settings file degrades to defaults instead of blocking boot, same
"never crash on this" precedent `sfx.py`/`music.py` already set for audio
itself. A tiny new `ui_tick` sfx plays on every SFX Volume click, doubling
as instant feedback for the level just set.

Known gaps: no master mute-all toggle (Music and SFX are independent
sliders only), and no volume control on the title screen itself (the
pause menu's Settings only exists once a run is in progress -- background
music already plays there, just isn't adjustable until you start/continue
a game). Mouse buttons, hotbar 1-9, Esc and the F-keys are not rebindable
(see reserved-key note above).

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

The inventory screen (`I`) is a two-panel "character sheet": a left column
with the player's portrait, one bordered slot per entry in
`game/inventory/equipment.py`'s `SLOTS` (Head, Body, Legs, Boots, Accessory)
and a
stats block (HP / total Defense / the selected hotbar item's Attack), and a
right-side bag grid (the same 20 inventory slots as before). Equipping
moves the item out of the bag into its slot (click an armor item in the
bag); unequipping moves it back (click the occupied slot). Every occupied
slot -- bag or equipment -- gets a border colored by `ItemDef.rarity`
(common/uncommon/rare/epic). `Equipment.total_defense()` sums every
equipped item's `defense` and is subtracted from incoming contact damage in
`combat_system.resolve_contact_damage`, floored at `MIN_DAMAGE_AFTER_DEFENSE`
so armor reduces damage but never fully negates it. Worn pieces can also
emit light (`ItemDef.light_emit`, same 0-15 scale as torches): the
brightest equipped piece is added as a mobile light source at the player
(the Arcane Helm). The weapon slot in
combat is still the hotbar selection, not a separate equip slot -- see
"Controles" above.

Hovering any occupied slot (bag or equipment) shows a floating tooltip
next to the cursor (`Renderer._draw_item_tooltip`): name (colored by
rarity), category/rarity, its wrapped `ItemDef.description`, and a
category-specific stat block (`_item_tooltip_stat_lines` -- mining power
for tools, damage/melee-or-ranged for weapons, defense/slot for armor,
heal amount for food, durability and value where they apply). Clamped to
stay fully on screen even near a window edge.

Right-clicking a bag item is a quick-action shortcut
(`InputHandler._handle_inventory_right_click`): armor equips immediately
(same as the existing left-click equip path), anything else swaps places
with whatever's in the *currently selected* hotbar slot
(`Inventory.swap_slots`) -- a fast way to load the hotbar without
dragging. Equipment slots aren't a right-click target (unequip already has
its own left-click action).

## How the Summoner class works

`player.class_id` (`game/entities/class_registry.py`) picks between two
classes, chosen once at the class-select screen (see "Controles" above):
**Warrior**, the default, fights with any sword or bow exactly as before;
**Summoner** fights entirely through a summoned minion and can't swing a
sword or fire a bow at all. Every `ItemDef` weapon has a `weapon_class`
(`"normal"` by default, `"summon"` for the two summon rods below) and
every `ClassDef` lists which `weapon_class`es it allows --
`combat_system.try_attack` checks the selected item's `weapon_class`
against the player's class before doing anything else, and
`Player.blocked_weapon_class_reason()` surfaces a toast ("Your Warrior
class can't use this") the same way a missing pickaxe already does for
mining.

Casting a summon rod (left-click with it selected) summons its minion at
the player's position, replacing whatever summon was already active --
only one summon is ever out at a time. Two rods exist so far: the **Twig
Rod** (craftable anywhere from 8 Wood -- also handed to a Summoner for
free the moment the class is picked) casts a **Twig Sprite**; the
**Iron Rod** (a Workbench recipe needing a smelted Iron Bar) casts a much
stronger **Iron Guardian**, drawn with `assets/flying-head.png`
(`assets.load_iron_guardian_animations`) -- a sheet that was sitting
completely unused after an earlier pass moved the Duskwing enemy to
`Bat.png` instead. Twig Sprite still has no dedicated art (the flat
glowing shape every summon used to render). A summon (`game/entities/summon.py`,
`summon_ai.py`) flies toward the nearest alive enemy within its
`seek_radius_tiles` and attacks once in range (`combat_system.
resolve_summon_attacks`, on the same "AI moves, combat_system deals the
damage" split enemies already use), otherwise it hovers near the player
and snaps back if it strays past `follow_distance_tiles`. Movement is
flying-style (gravity ignored, no wall/ledge avoidance) -- the same
deliberate simplification already used for the Duskwing enemy -- and, in
this first pass, a summon **cannot be damaged**: no enemy in the game
currently has any way to attack a friendly entity, so summons are safe by
omission rather than by design. There's no HUD indicator for the active
summon yet, and only these two tiers exist -- more classes/rods/summons
would follow the exact same `ClassDef`/`SummonDef` registry pattern.

## How skills/leveling work

Six independent RuneScape-style skills (`game/skills/`) -- **Attack,
Defense, Magic, Mining, Crafting, Hitpoints** -- each with its own XP bar
and level 1-99, using the real RuneScape XP curve
(`game/skills/xp_table.py`: `xp(99) = 13,034,431`, an intentionally steep
curve where early levels are fast and 99 is a genuine long-term goal, the
whole appeal of the genre). Open the Skills screen with `K`.

XP is granted right inside whichever function already owns the relevant
transaction, not from a central "XP manager": landing a melee or ranged
hit grants Attack XP (plus a kill bonus), a summon landing a hit grants
Magic XP, taking damage grants Defense XP, breaking a tile grants Mining
XP, and a successful craft or completed smelt grants Crafting XP.
Hitpoints never gets XP directly -- like real RuneScape, it passively
earns 1/3 of every Attack/Defense/Magic grant and raises `player.
max_health` by `HITPOINTS_HP_PER_LEVEL` (10) on each level-up (healing
you by the same amount), since every combat skill also trains
survivability.

Every skill has a real effect, not just a number going up: Attack and
Magic scale weapon/summon damage (`ATTACK_DAMAGE_PCT_PER_LEVEL` 5% and
`MAGIC_DAMAGE_PCT_PER_LEVEL` 8% per level after 1, so the floating
numbers actually change); Defense adds a flat bonus on top of equipped armor
via `combat_system.player_total_defense(player)`; Mining scales mining
power; Crafting boosts its own XP gain and can refund a material. Leveling
a skill also earns it points (1 per level) spendable on that skill's own
3-tier skill-point tree (`game/skills/skill_tree_registry.py`, levels
10/30/50) -- click a skill in the Skills screen to see its tree, then
click an eligible (green-bordered) node to unlock it. Tiers 2 and 3 also
require the previous tier specifically (`SkillNodeDef.requires_node_id`),
drawn as a line connecting the node boxes (gold once unlocked through),
so it's a real chain to climb rather than 3 independently-gated boxes.
`Skills.available_points` is derived from `level - 1 - unlocked_count`,
not stored separately, so it can never drift out of sync with what's
actually unlocked.

Two more places show skill progress without opening the full Skills
screen: the character sheet (`E`) has a compact 2-column, 6-skill level
grid below its HP/Defense/Attack/Combat Lv block, and an always-visible
top-left HUD bar shows `Combat Lv N` plus a % bar
(`Skills.combat_level_progress_ratio`, the average of Attack/Defense/
Magic/Hitpoints' individual progress toward their next level -- Combat Lv
itself has no XP track of its own, so this is the closest honest
approximation of "how close to the next tick").

A summon's Magic damage bonus is applied live on each hit
(`combat_system.resolve_summon_attacks`), so leveling Magic mid-fight
shows up on the next number that pops -- recasting the rod is not
required. Swift Familiar's speed/interval bonus is still baked in at
cast time (`combat_system._try_summon_cast`) as a per-instance override
on `move_speed`/`attack_interval_s`.

## How to create a recipe

Add one `RecipeDef` entry in `game/crafting/recipe_registry.py`:
`ingredients` (a tuple of `(item_id, quantity)` pairs, all must already
exist in `item_registry.py`), `result_item_id`, `result_quantity`, and
`station_tile_id` (`None` for craftable-anywhere-by-hand, or a tile id like
`tile_registry.WORKBENCH_ID` to require the player stand within
`STATION_SEARCH_RADIUS_TILES` of that tile). No other file needs to change
-- the crafting screen (`C`, or click a placed Workbench -- see below)
lists every registered recipe automatically, grouped by the result item's
category (see "How the crafting screen is laid out" below), and scrolls
(mouse wheel) once the list outgrows `CRAFTING_VIEWPORT_HEIGHT` so the
panel never grows into the HUD no matter how many recipes get added
later. It won't be craftable (or even show its name) until the player has
discovered every one of its ingredients -- see "How recipe discovery
works".

Crafting and smelting are two separate screens now (user feedback:
clicking a Workbench or a Furnace should open *that station's* screen,
not one combined menu). `InputHandler._try_open_station_screen` fires on
a left-click: if the clicked, in-range tile is `WORKBENCH_ID` it opens
Crafting (`game_app.crafting_open`); if it's `FURNACE_ID` it opens the
Furnace screen (`game_app.furnace_open` -- see "How the furnace works")
instead. It's skipped while the selected hotbar item is a tool
(`ItemDef.is_tool`), so holding a pickaxe out and clicking a placed
station still mines/relocates it rather than always opening its screen.
`C` still toggles Crafting from anywhere as a shortcut (handy for the
station-less recipes); there's no keyboard shortcut for the Furnace
screen, only the click, since every furnace recipe needs one nearby
anyway. Both screens close on `Esc`, and a small "Click: Craft" /
"Click: Furnace" floating hint (`Renderer._draw_station_prompt`) appears
over a nearby station's tile whenever its screen isn't already open.

## How the crafting screen is laid out

A grid of icon cells on the left (several recipes side by side, not one
tall row each -- 7 columns, sized generously after user feedback that the
original 5-column layout felt cramped) plus a fixed details panel on the
right for whichever cell the mouse is currently over
(`Renderer._draw_recipe_details`: name, station badge, full ingredient
list with live counts, and a status line -- "Click to craft", "Missing
ingredients", "Needs Workbench nearby"). The grid itself only needs to
carry an icon, a quantity badge and a thin colored border for status
(green=ready, grey=missing ingredients, amber=needs its station), since
the actual breakdown lives in the details panel -- hovering is what
reveals it, clicking is still what crafts it. Smelting recipes never
appear here at all anymore -- they're the Furnace screen's own queue (see
"How the furnace works").

Cells are grouped by what the result item's `ItemCategory` *is*
(`_CATEGORY_SECTION_ORDER` in `renderer.py`: Building, Structures &
Utility, Tools, Weapons, Armor, Ammo, Materials) rather than by where
they're crafted -- a layout a player recognizes at a glance ("I want a
weapon" beats "I wonder which station this needs"); each cell's own
station requirement (`_station_label`: "Anywhere", "Workbench", ...) shows
up in the details panel instead.

A filter bar (`Renderer._draw_crafting_filter_bar`) sits between the title
and the grid: five rarity tabs (All/Common/Uncommon/Rare/Epic --
`CRAFTING_RARITY_TABS`, filtering on the *result item's* `ItemRarity`) on
the left, and a "Craftable now" toggle on the right that hides every
recipe that isn't currently `has_ingredients` + `is_near_station` (i.e.
what the player could click right now with what's in their bag) -- direct
answers to "show recipes by rarity" and "filters for what I can make with
what I have" user feedback. Both live as session-only state on `GameApp`
(`crafting_filter_rarity`, `crafting_filter_craftable_only`, not
persisted across save/load) and are threaded through every crafting-grid
helper (`_recipe_sections`, `_crafting_layout`, `crafting_max_scroll`,
`recipe_at_screen_pos`, ...) as optional trailing params, so every old
call site that only cares about discovery (tests included) still works
unfiltered by just not passing them.

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
furnace_system.py`) for turning ore into bars, with its own screen
(opened by clicking a placed Furnace -- see above) separate from
Crafting. Unlike a crafted item, smelting is a *started-then-collected*
transaction, not an instant one, because burning takes real time -- and
unlike a single craft, it's a **queue**: the player deposits a whole
stack of ore and fuel, and the furnace keeps converting one recipe's
worth at a time on its own until it runs out, instead of needing a click
per batch (user feedback: "quero funace queue, aonde eu insiro o carvao
e os minerios e ele vai fabricando").

Each furnace tile gets its own 2-slot input hopper
(`FurnaceManager.input_at`, keyed by that tile's position so multiple
placed furnaces run independently) -- slot 0 is fuel, slot 1 is ore
(`FURNACE_FUEL_SLOT`/`FURNACE_ORE_SLOT`). The Furnace screen's bag grid
routes a clicked inventory item into whichever slot accepts it
automatically (`smelt_registry.all_fuel_item_ids()`/`all_ore_item_ids()`
decide "fuel" vs. "ore" vs. "furnace can't use that"; a slot already
holding a different item rejects the deposit rather than mixing).
Clicking the fuel or ore slot itself withdraws it back to the bag.

`FurnaceManager.update(dt)` (polled every frame by `GameApp`) advances
whichever job is active per furnace, same `FurnaceJob`/`smelt_time_s`
timing as before; the moment one finishes, it's granted straight to the
player's inventory via `collect_and_discover` (so a first Iron Bar can
itself unlock the Iron Pickaxe recipe) and announced with a "ready!"
toast -- there's no separate output slot to collect from. Right after
clearing a finished job, `update()` also tries `_try_autostart` on every
furnace with an input hopper: if its fuel/ore slots still hold enough for
`smelt_registry.recipe_for_ore(ore_slot.item_id)`, it consumes another
batch and starts the next `FurnaceJob` immediately, no player action
needed -- this loop is the whole queue. `FurnaceManager.start_smelt` (the
original one-shot, instant-consume-from-inventory path) still exists
untouched for anything that wants a single smelt with no setup, but the
Furnace screen itself only ever uses the deposit+auto-restart path above.

Four ores that were catalog-only in earlier phases have a real
obtain-then-use path this way: Iron Ore, Topaz, Sapphire and Emerald each
smelt into their own Bar. Iron Bar crafts Iron tools/armor and can be
re-smelted (2 Iron Bars + 2 Coal) into a Steel Bar for the next
mining/armor tier. Topaz, Sapphire and Emerald Bars combine at a
Workbench into an **Arcane Bar**, the magic-tier material (see "How
magic-tier gear works").

## How magic-tier gear works

Visit all three non-forest biomes for Topaz (desert), Sapphire (snow) and
Emerald (jungle), smelt each into its Bar, then craft an **Arcane Bar** at
a Workbench (one of each). That bar unlocks three recipes, each with a
mechanic rather than only a bigger number:

- **Arcane Pickaxe** -- mines faster than steel (`mining_power` 9) and
  rolls `fortune_chance` (`ARCANE_PICKAXE_FORTUNE_CHANCE`) for a second
  copy of whatever the tile dropped.
- **Arcane Staff** -- a Warrior ranged weapon with no ammo. Bolts fly
  straight (no gravity arc), scale with the Magic skill, and grant Magic
  XP. Summoners already train Magic through minions and cannot fire it
  (`weapon_class` stays `"normal"`).
- **Arcane Helm** -- defense above a Steel Helmet, plus `light_emit` so
  wearing it lights nearby tiles like a moving torch.

A later itemization pass completed the rest of the tier from the same
Arcane Bar: **Arcane Body/Greaves/Boots** (filling out the armor set
alongside the Helm), an **Arcane Sword** (melee, with a chance to crit)
and an **Arcane Rod** (casts an Arcane Familiar, the Summoner's version
of this tier) -- see "How item stats work (crit, move speed)" below.

## How item stats work (crit, move speed) and the full gear ladder

A big itemization pass (user-requested: "melhore todo o sistema de
itemização, builds por classe, status de cada item, crie novos itens
late games, novas armas etc", run as 3 parallel agents in isolated git
worktrees) filled out weapon/armor progression end to end and added two
new stats. Full blow-by-blow (every new item id, exact stats, and the
known gaps) lives in TODO.md under "Itemization overhaul" -- this is the
shape of it:

- **`ItemDef` gained `crit_chance`, `crit_damage_mult` and
  `move_speed_bonus`** (`game/items/item.py`). Crit is rolled in
  `combat_system.py` for melee, ranged, *and* summon attacks (reading
  the currently-equipped rod's own `crit_chance` for the summon case) --
  every class benefits from the same system, not just whoever swings a
  sword. `move_speed_bonus` sums across every equipped slot
  (`Equipment.total_move_speed_bonus()`, same pattern as
  `total_defense`) and adds straight onto `PLAYER_MOVE_SPEED` in
  `Player.move_left`/`move_right`. Both show up on the item tooltip
  (`Renderer._item_tooltip_stat_lines`) when non-zero.
- **A real weapon ladder now exists at every material tier**, not just
  for pickaxes/armor: Wood -> Iron -> Steel -> Arcane -> Voidsteel for
  swords (8 -> 14 -> 20 -> 28 -> 38 damage) and a parallel Wood -> Iron
  -> Steel bow line, plus a summon rod at every one of those tiers
  (Twig Sprite 7 -> Iron Guardian 14 -> Steel Colossus 21 -> Arcane
  Familiar 27 -> Void Wraith 34 damage) so the Summoner class always has
  an equivalent option to whatever the Warrior just unlocked.
- **A new post-Arcane endgame tier: Voidsteel.** A universal (every
  biome, not gem-locked like Topaz/Sapphire/Emerald), very rare, very
  deep-only ore (`VOID_ORE_ID`, `game/world/tile_registry.py` +
  `world_generator.py`) smelts into a **Voidsteel Bar** (the slowest
  smelt in the game) that crafts a full weapon/armor/accessory/summon
  set above everything that existed before this pass -- see TODO.md for
  every stat. The final boss's loot line also grew: 2 new recipes
  (**Slime King's Fang**/**Bulwark**) consume the existing
  `slime_king_core` drop alongside the pre-existing Crown, so farming
  the Slime King repeatedly is a real, farmable side-grade path to the
  same power level.
- **Accessories went from 1 (Grapple Hook) to 7**, most of them purely
  passive stat items requiring zero new code -- `Equipment.total_defense`/
  `total_light_emit`/`total_move_speed_bonus` already sum every equipped
  slot including accessory, so an accessory with `defense`/`light_emit`/
  `move_speed_bonus` set and `accessory_kind=None` (i.e. not an *active*
  E-triggered behavior like Grapple Hook) just works.

## How the Personal Chest works

A craftable, placeable storage tile (`tile_registry.PERSONAL_CHEST_ID`,
8 Wood, anywhere). **T** while standing near one opens a two-grid panel
(bag on the left, stash on the right); click a stack to move as much as
fits. Every placed Personal Chest shares the same stash
(`Player.personal_chest`) -- contents follow the player, not the tile, so
mining a chest drops the furniture item without dumping the items inside.
The world-loot Chest inside structures is a different tile (mine it for
a random drop); this one is storage. T prefers an NPC if both are in
range. The stash round-trips through save/load; old saves without the
field start empty. Texture is `assets/Items/Boxes/Box3`.

## How ground AI steps over ledges

`tile_collision.try_step_up(entity, world, direction)` climbs a genuine
1-tile ledge onto flat ground instead of treating it as a wall; a real
(2+ tile) obstacle is left alone. `WALK`-type enemies (`enemy_ai._update_walk`)
call it every frame before committing to a direction, alongside
`is_solid_ahead` (turn around if blocked and unclimbable) and
`has_ground_ahead` (turn around before walking off a ledge) -- without it,
ground AI would reverse at every bump in the naturally-bumpy generated
terrain and never get anywhere.

`HOP`-type enemies (`enemy_ai._update_hop`, and the Slime King boss's own
`boss_ai._update_hop_movement`) call it too, right before the horizontal
`move_axis` each frame while airborne. A hop only sets its horizontal
velocity once, at launch, and never revisits it mid-flight, and
`move_axis` zeroes that velocity outright the instant any part of the
mover's hitbox clips a solid tile -- so a 1-tile bump anywhere under a
hop's arc used to stall it dead on contact; since the AI re-aims at the
same target every following hop cycle, the visible result was the
enemy/boss looking like it was bouncing in place against an invisible
wall (user-reported: "fica pulando no mesmo lugar infinito").

Both `is_solid_ahead` and `try_step_up` check every tile row an entity's
height actually spans (`tile_collision._entity_row_span`), not just a
single mid-height row -- a no-op for the ~1-tile-tall regular enemies
(their span is always one row already) but necessary for the 1.8-tile-tall
Slime King boss, whose hitbox can clip a bump at its feet that a check at
its mid-height alone would miss entirely.

Both also probe from `tile_collision._leading_tile_column(entity, direction)`
rather than always exactly `center + direction`: for anything up to a tile
wide the two are identical, but the 2.4-tile-wide Slime King boss's real
leading edge (what `move_axis`'s own collision resolves against) can sit a
full tile or more past its own center+1. On a perfectly smooth staircase
where each column individually only ever rises 1 tile, that let the boss's
wide body catch a *2-tile* total rise across its own footprint that a
center-only probe never looked at, freezing it permanently (user-reported,
after the single-bump fix above had already shipped: "o boss ainda fica
preso em um terreno desnivelado"). `try_step_up` also takes a
`max_step_tiles` (default 1, matched to the 1-tile bumps every other
entity needs); the boss passes 2, sized to the worst-case rise its own
width can catch -- a genuine 3+-tile wall is still left blocking it.

## How to create an enemy

Add one `EnemyDef` entry in `game/entities/enemy_registry.py`: `ai_type`
(`AIType.WALK` ground patrol/chase, `AIType.HOP` slime-style periodic
jumps, `AIType.FLY` gravity-free hover/chase, or `AIType.BOSS` for a
multi-phase boss -- see "How the Slime King boss works" below), `max_health`,
`contact_damage`, `move_speed` (px/tick -- see "Velocity units" above),
`width_tiles`/`height_tiles`, `color`, `spawn_weight` (relative chance
among all enemies when the spawner picks one), `spawn_time`
(`SpawnTime.ANY`/`DAY`/`NIGHT` -- gates which enemies `EnemySpawner` will
even consider based on `WorldClock.is_night`; Duskwing is `NIGHT`-only,
which is how "different enemies at night" is satisfied), `biome_id` (`None`
for any biome, or a `biome_registry` id like `DESERT_ID` to restrict it to
that biome -- Scorpion is desert-only, spawned by checking
`world_generator.biome_at` at the candidate spawn column), and optionally
`drop_item_id`/`drop_chance`/`drop_min`/`drop_max`. Frost Hopper (Snow) and
Swamp Mosquito (Jungle) are the other two exclusive enemies, same `biome_id`
gating as Scorpion. To add a genuinely new
*behavior* (not just new stats on an existing one), add a 4th `AIType` and
a matching `_update_*` function in `enemy_ai.py`.

Enemy art lives in `assets/Enemies/`. **Duskwing** uses `mini bat.png`
(32px cells: hover flap on row 0, dive on row 1). `Bat.png` is a 5x4 of
near-identical poses so it looked frozen in place. Flyers spawn several
tiles above the grass so they hover instead of sitting on the ground
until the player walks into chase range. **Slime** and **Slime King**
reuse `Mini_Slime_Idle/Walk/Hurt.png` (32px strips; the king is just
scaled up), feet-anchored so hops sit on the ground. **Scorpion** uses
`Scorpian/Idel.png`, `Walk.png` and `Attack.png` (3-frame 32px strips).
**Frost Hopper** reuses those Mini_Slime sheets with an icy `_tinted` wash;
**Swamp Mosquito** uses `mosquito.png` (48px cells, wing flap on row 0).
Crawler has no matching sprite (`assets/20 Enemies.png` is a watermarked promo) so it stays
a flat colored rectangle in `_draw_enemies`. To give a new enemy a sprite,
add it to `assets.load_enemy_animations` keyed by `EnemyDef.id`.

## How the Slime King boss works

The first boss (Phase 10, `game/entities/boss.py` + `boss_ai.py`). A
`Boss` is just an `Enemy` subclass with extra phase-tracking fields, so it
gets melee/ranged/summon damage, contact damage, drops and its transient
(not-saved) lifetime for free from the existing `combat_system`/`GameApp`
machinery -- only its movement/attacks and the projectile it fires needed
new code.

**Summon:** craft a **Slime Core Idol** (Workbench: 20 Slime Gel + 5 Iron
Bar) and press **G** with it selected (`Player.use_selected_summon_item` ->
`GameApp.try_summon_boss`) to spawn the Slime King beside you -- blocked
(idol not consumed) while one is already alive.

**Phases**, keyed off remaining-health ratio and permanent once entered
(health only ever goes down):
- **Phase 1** (>66%): hops toward the player (same shape as the regular
  Slime's `HOP` AI, just bigger/harder), contact damage, and already lobs a
  gravity-arced **Slime Lob** projectile on a cooldown -- `EnemyProjectile`
  (`game/combat/enemy_projectile.py`) is the enemy-owned mirror of the
  player's `Projectile`, resolved against the player by
  `combat_system.update_enemy_projectiles`. (Ranged attacks used to only
  unlock at phase 2; a player who never brought the boss that low would go
  a whole fight without ever seeing a projectile, so the lob now fires from
  the very start.)
- **Phase 2** (<=66%): hops and lobs faster.
- **Phase 3** (<=33%, enrage): summons 2 regular Slimes once, hops/lobs
  even faster, the lob becomes a `SLIME_KING_SPREAD_COUNT`-projectile fan
  (`boss_ai._fire_projectiles`) instead of a single shot, and every landing
  sets `Boss.stomp_pending` -- a shockwave (`combat_system.resolve_boss_stomp`)
  that damages the player within `SLIME_KING_STOMP_RADIUS_TILES` even
  without a direct hitbox overlap, unlike ordinary contact damage.

**The hop leads its target** (`boss_ai._update_hop_movement`) -- it used
to aim at wherever the player was standing the instant it launched, then
commit to that fixed horizontal velocity for the whole arc, an easy dodge
made worse by `SLIME_KING_MOVE_SPEED` originally being *slower* than the
player's own move speed. It now solves for the player's *predicted*
position at landing time (current position + their own `x_vel` * the
arc's time-of-flight, derived from `SLIME_KING_HOP_IMPULSE`/`GRAVITY`),
capped at `move_speed * phase_mult * SLIME_KING_HOP_LEAD_SPEED_MULT` so a
far-away target doesn't demand an absurd lunge -- and is faster than the
player outright.

**It steps over bumps mid-hop** (`tile_collision.try_step_up`, called
right before the horizontal `move_axis` in `boss_ai._update_hop_movement`,
same as every regular `HOP`-type enemy's `_update_hop` -- see "How ground
AI steps over ledges" below, including why the boss passes
`max_step_tiles=2` where every other entity uses the default of 1). At
`SLIME_KING_HEIGHT_TILES`/`SLIME_KING_WIDTH_TILES` (1.8 x 2.4) the boss's
hitbox spans two tile rows and can reach a leading-edge column a full 2
tiles taller than the one under its own center, even on a perfectly smooth
1-tile-per-column staircase -- either used to zero its horizontal velocity
outright (`move_axis` zeroes the matching velocity component on any
collision) and strand it at the bump until the next hop cycle re-aimed
from scratch, looking like it was bouncing in place forever. A real (3+
tile) wall still blocks it.

A persistent bar at top-center shows its name, HP and current phase number
from the moment it's summoned (not just once damaged, like the small
floating bar every other enemy gets). **Drops:** a guaranteed **Slime
King's Core** (`drop_chance=1.0`) plus a coin bounty
(`BOSS_COIN_BOUNTY`) -- the Core crafts into the **Crown of the Slime
King** (Workbench: 1 Core + 3 Steel Bar), the best head armor in the game.

Known gaps: no arena/leash keeps the player from wandering off mid-fight;
summoning doesn't check the ground under it is solid (same simplification
the Summoner's summon rod already uses); no dedicated art/audio; not
persisted across save/load (same transience as regular enemies).

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
Snow and Jungle all currently share the same tree system unchanged. Snow and
Jungle each have a biome-exclusive enemy (Frost Hopper / Swamp Mosquito),
matching Desert's Scorpion. "Cave"
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

Add one `NpcDef` entry in `game/npcs/npc_registry.py`: `dialogue` (a tuple
of lines shown in order -- click Next or the panel body to advance),
`shop_stock` (a tuple of `ShopOffer(item_id, price)` -- empty for a
talk-only NPC like the Guide), `spawn_condition` (`"always"`, `"wealth"`,
or `"discovered_item"`), and for `"discovered_item"` a `spawn_item_id`
the player must have obtained at least once. Shop `item_id`s must already
exist in `item_registry.py`, and `price` must be strictly greater than
that item's `value` so buying then selling can't print coins. No other
file needs to change -- `npc_spawner` assigns a home, the T-to-talk
panel lists whatever is registered, and a `"wealth"`/`"discovered_item"`
NPC toasts `"X has arrived!"` the moment they qualify.

## How NPCs work

Three townsfolk, spawned from named conditions rather than wandering in
at random:

- **Guide** (`spawn_condition="always"`): already there at run start.
  Lives in the nearest House (Phase 7) if one is within
  `NPC_GUIDE_MAX_HOUSE_DISTANCE_TILES` of world-center spawn; otherwise
  stands on the surface a few tiles left of spawn so they're actually
  findable. Dialogue is a short tutorial (mine, craft, houses, skills,
  the other two NPCs' unlocks). No shop.
- **Merchant** (`"wealth"`): appears once bag wealth (sum of
  `ItemDef.value * quantity`, not counting equipped gear) reaches
  `NPC_MERCHANT_MIN_WEALTH`. The starting wood pickaxe is worth 10, so
  this is "you've gathered a bit of loot", not "you spawned". Sells
  convenience goods (torches, arrows, apples, wood) and buys anything
  except coins.
- **Blacksmith** (`"discovered_item"`, `iron_bar`): appears once you've
  obtained an Iron Bar (smelted or looted from a Chest). Sells tools and
  armor (Wood Sword through Steel Pickaxe) as a paid shortcut around
  crafting.

Homes prefer unused Houses, nearest to spawn first, then a surface
fallback that skips columns whose tile above the ground isn't air (so
nobody spawns inside a tree). Assignment is a pure function of
`(seed, registry order)` -- the same NPC always claims the same home
for a given seed, regardless of the order conditions unlock. Once
present they stay, even if wealth later drops below the Merchant
threshold (flickering in and out would feel like a bug).

Press **T** while within `NPC_INTERACT_RANGE_TILES` to talk (a nameplate
prompt appears when you're close enough). Esc / walking out of range /
opening I, C, or K closes the panel. Click Shop on a Merchant or
Blacksmith to buy (left list, costs coins) or sell (right bag grid,
grants `ItemDef.value` coins per item). A full bag with no coin stack
sells the whole clicked stack so the payment can occupy that slot;
otherwise one item. Currency is the `coin` item --
not crafted, not mined, only earned by selling. Shops have infinite
stock; a buy that can't fit in the bag refunds the coins (same
all-or-nothing rule as crafting). NPCs are not persisted: on load,
conditions are re-derived from player state and they reappear at the
same homes, without re-toasting an arrival.

NPCs don't walk, fall, or fight (no pathfinding/schedule system), and
they have no dedicated sprites -- they're a simple colored humanoid
plus a nameplate, the same honest gap enemies already have. Mining the
floor out from under one leaves them floating. See TODO.md for these
and other known gaps.

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
health, inventory, equipment, `discovered_item_ids`), any in-progress
Furnace jobs, and every furnace's queued input hopper (deposited
fuel/ore, `FurnaceManager.inputs` -- so saving mid-queue doesn't discard
whatever stack was still smelting). **Only modified chunks are saved, and only their changed
tiles** -- `Chunk.dirty` already existed for exactly this (set the moment
any tile is mutated); at save time each dirty chunk's live tiles are
diffed column-by-column against a freshly recomputed procedural baseline
(`generate_column(seed, x)` -- a cheap pure function, the same cost
already paid every chunk load/unload) and only the `(local_x, y, tile_id)`
triples that actually differ are written out. Loading replays those diffs
on top of ordinary procedural generation, so an unmodified chunk needs no
saved data at all.

Not persisted (transient/regenerable, same as what already happens after
Restart): enemies, NPCs, projectiles, particles, on-screen notifications.

Two pause-menu buttons, Save and Load (`GameApp.save_game`/`load_game`),
wired through `InputHandler._handle_pause_click` exactly like the
existing Restart button. Save writes the file and pushes a "Game saved"
toast; Load reads it (a "No save found" toast and a no-op if the file
doesn't exist) and rebuilds `world`/`player`/`world_clock`/
`furnace_manager` from the deserialized data, resetting the same per-run
transient state `_new_run` already resets on Restart. Their buttons are
the UI reskin's Save/Load wood-plank art (see "How the UI theme works")
-- no hand-drawn icon needed for these two anymore.

## How the debug tools work

Two independent layers, both in `game/core/debug_overlay.py` /
`GameApp`:

- **F3** toggles the read-only debug HUD (FPS, seed, position, chunk,
  loaded chunk count, HP/regen, zoom, enemy/NPC counts, biome, day/time/
  ambient) -- unchanged, always available, no state it can accidentally
  mutate.
- **F4** toggles `GameApp.debug_mode`, a dev-session flag (like
  `prefs` -- not reset by `_new_run`/Restart/Load, since it has nothing
  to do with "one playthrough") that gates seven cheat actions, **F5-F11**,
  so a stray keypress during normal play can never trigger one. While on,
  a red "DEBUG MODE" banner plus the shortcut list is always shown (even
  with F3's own overlay off), stacked above it when both are on.

| Key | Action |
|---|---|
| F5 | `debug_unlock_all_recipes` -- marks every registered item id as discovered (`Player.discovered_item_ids`). Recipe visibility is ingredient-discovery-based, not a recipe-id allowlist (see `crafting_system.is_recipe_discovered`), so this is the whole item catalog, not the recipe list |
| F6 | `debug_reveal_map` -- `World.reveal_map_fully()` -> `exploration.reveal_all`, the same per-cell sampling the real Map (M) fog-of-war reveal uses, just with no radius limit. Forces every not-yet-loaded chunk to generate (cheap and deterministic, a one-time cost) |
| F7 | `debug_restock` -- full heal plus `DEBUG_RESTOCK_COINS` (999) Coins |
| F8 | `debug_spawn_all_bosses` -- one of every `AIType.BOSS` `EnemyDef` (currently just the Slime King), spawned as real `Boss` instances beside the player. Bypasses `try_summon_boss`'s idol/one-at-a-time gating entirely -- this is a raw debug spawn, not the normal G-key summon path |
| F9 | `debug_spawn_all_enemies` -- one of every non-boss `EnemyDef` (Slime, Crawler, Duskwing, Scorpion), each offset `DEBUG_SPAWN_SPACING_TILES` apart so they don't stack on landing |
| F10 | `debug_teleport_to` -- teleports to the current mouse cursor's world position (`camera.screen_to_world`), clearing velocity/jump state the same way a respawn does |
| F11 | `debug_teleport_to_spawn` -- back to `Player.spawn_x/spawn_y` (the last Checkpoint, or the world spawn if none was ever touched) |

None of these validate the destination/target is safe (solid ground under
a teleport, a sensible spot for a spawned enemy) -- same "developer
convenience, not a polished feature" scope as the rest of this list; the
regular world-generation/collision systems settle anything that lands
oddly on the very next physics step.

## How the UI theme works

A user-supplied asset pack landed in `assets/validar` (also reachable as
`assets/Validar` -- Windows paths are case-insensitive) with a request to
find sprites worth using. It turned out to be a top-down zombie-survival
pack: its `Character`/`Enemies`/`Objects/Nature` art is drawn as seen
from directly above (a walking character's head is visible with the body
"flattened" beneath it), and thematically it's guns/zombies/cars/
shipping containers. None of that fits this game -- a strict side-view
2D platformer with a fantasy mining/crafting theme -- so using it for the
player, an enemy, or decoration would read as visually wrong (something
drawn for a bird's-eye view, standing in a world seen from the side) on
top of not matching the setting. See `tests` -- there's no headless test
for "does art look right", so this call was made by rendering sample
sprites and inspecting them directly, not guessed from filenames.

The pack's `UI/` folder is different: plain 2D icons and frames with no
world perspective to clash, so every panel/button/health-bar/item-slot in
the game was reskinned with it (`game/rendering/assets.py`'s
`load_ui_theme`, `game/rendering/renderer.py`):
- **Health bar** (`Renderer._draw_hp_frame_bar`): the pack's `HP-Bar.png`
  frame (whole-image integer-scaled, not 9-sliced -- it's meant to be
  shown at its own aspect ratio) with `HP.png` cropped to the current
  health ratio and stretched into the frame's fill track (measured from
  the frame's own hollow interior, `hp_bar_fill_track` in `load_ui_theme`,
  not guessed). Shared by the player HUD bar and the Phase 10 boss bar.
- **Panels** (`Renderer._draw_nine_slice`, used by `_draw_panel_chrome` --
  Inventory/Crafting/Skills/Personal Chest/NPC dialogue all share it): a
  generic, cached 9-slice -- corners/edges are scaled-up copies of the
  source frame's native border, the middle stretches -- so one small
  ~140x90 source panel reads cleanly at this game's much larger and
  differently-shaped panels instead of one blurry whole-image stretch.
  Automatically clamps its border down for a panel too short/narrow to
  fit it (e.g. the crafting panel when almost nothing is discovered yet)
  so corners never overlap into a corrupted-looking result.
- **Item slots** (`_draw_item_slot`, plus the hotbar and crafting-grid-cell
  call sites): the pack's cell texture, whole-image-scaled per slot (a
  distinct "chosen" texture for the selected hotbar slot / hovered slot),
  with the existing rarity-tier or ready/missing/needs-station status
  border color kept on top -- the reskin only replaces the background,
  not the functional color-coding.
- **Buttons** (`Renderer._draw_ui_button`; title screen, pause menu + its
  Settings sub-screen, NPC dialogue Shop/Next/Talk/Close): a wood-plank
  button swapping in the pack's own "pressed" art on hover. Buttons whose
  baked-in text already matches the action (Play/Save/Load/Settings/Quit)
  draw no separate label; everything else (Restart, Zoom -/+, Back, Shop,
  Next, Talk, Close) uses the textless "Blank" plank with a drawn label.
  The pause menu's buttons changed from square icon buttons to landscape
  plaques (`PAUSE_BUTTON_WIDTH`/`HEIGHT`) to match the art's own
  proportions instead of squashing an oval into a square.

The old `assets/Menu/Buttons/Menu_jogo/` icon set (and its hand-drawn
Save/Load fallback icons, `_build_save_icon`/`_build_load_icon`) is fully
unused after this pass and was deleted rather than left as dead code.

## Known limitations

- Save is single-slot (`saves/save.json`) -- no multiple save files or a
  picker UI. Enemies, NPCs, projectiles, particles, and on-screen
  notifications aren't persisted (see "How save/load works"). NPCs
  reappear from their spawn conditions on load.
- Only one boss exists so far, with no arena/leash mechanic and no
  persistence across save/load (see "How the Slime King boss works").
  NPCs don't walk, fall, or take damage, shops have infinite stock, and
  they have no dedicated sprites (flat colored humanoids -- same gap as
  enemies; see "How NPCs work").
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
- Only 4 regular enemies (slime, crawler, duskwing, scorpion); slime,
  Duskwing and Scorpion use `assets/Enemies/` sheets, crawler is still a
  flat rectangle (see "How to create an enemy"). Slime King is the Phase
  10 boss and reuses the slime sprite at a larger size.
- Enemy kills grant loot directly to the player's inventory; there's no
  physical "item drop on the ground to walk over" entity yet.
- Armor has 5 equip slots (Head, Body, Legs, Boots, Accessory). Wood,
  Iron and Steel fill all four armor slots; magic-tier is the Arcane Helm
  (light) plus pickaxe/staff, not a full fourth armor set. Accessory is
  still the Grapple Hook.
- A furnace still only runs one `FurnaceJob` at a time (placing more
  furnaces is the way to parallelize), but it now auto-restarts from its
  own input hopper as long as enough deposited ore/fuel remains -- see
  "How the furnace works". Coal is the only fuel, one fixed quantity per
  recipe, no fuel-efficiency mechanic, and the input hopper is only 2
  slots (one ore type + one fuel type queued at a time, no mixed batches).
- Only one tile can grant a random drop (Berry Bush, via `TileDef.drop_pool`)
  -- every other tile still has exactly one fixed `drop_item_id`.
- Inventory/crafting UIs are click-driven panels (equip, unequip, craft,
  scroll), not full drag-and-drop or animated interfaces.
- The pause menu's Settings has Zoom, Music Volume, SFX Volume, and
  rebindable gameplay keys (see "How the Settings screen works") but no
  master mute-all toggle, no volume control on the title screen itself, and
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
