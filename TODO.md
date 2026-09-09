# Roadmap

Phases are built and validated in order; a phase is not started until the
previous one is playable and tested. See `README.md` for how to run the
game and its tests.

## Phase 1 — Playable prototype: DONE

- [x] Tile-based world with chunking (lazy load/unload)
- [x] Deterministic seeded generation: sky, dirt, stone, coal/iron ore, caves, bedrock floor
- [x] Player movement, gravity, tile collision, fall damage, respawn
- [x] Camera: smooth follow, world-bound clamping, zoom
- [x] Mining (tool-gated, timed) and building (placement requires adjacency)
- [x] Inventory: slots, stacking, hotbar, add/remove
- [x] Headless automated tests for all of the above

Known gaps, intentionally deferred (not fake/stubbed — simply not built yet):
- No save/load (closing the game discards the world)
- No lighting/day-night, crafting, combat, biomes, NPCs, bosses
- No real art (flat-colored placeholder tiles/player)

## Phase 2 — Data-driven item system: DONE
- [x] Expanded `ItemDef`: description, category, icon_key, rarity, value, damage, speed, max_durability
- [x] All 8 categories represented in `item_registry.py`: block, ore, material, tool, weapon, consumable, armor, decoration
- [x] Decoration category is fully functional end to end (wooden_crate: rare surface spawn -> mine -> place), not just data
- [x] Headless tests: category coverage, schema fields, crate spawn/mine/place

Known gap, intentionally deferred: material/weapon/armor/consumable items
(wood, wood_sword, wood_helmet, apple) exist as complete data but have no
obtain path yet (no trees, no crafting, no drops) and no usage mechanic
(no equip/attack/eat). They become obtainable and usable as Phase 3, 4 and
the equipment pass (below) land.

## Phase 3 — Crafting: DONE
- [x] Recipe schema (ingredients, quantities, result) + registry (`game/crafting/`)
- [x] Crafting stations: workbench tile, station-proximity gating (`STATION_SEARCH_RADIUS_TILES`)
- [x] Crafting UI (`C` key): shows every recipe, live ingredient counts, green/red ready state
- [x] Real trees (3-tile trunk + 3-wide canopy, deterministic slot-based placement) so wood is gathered from trees, not a floating log tile
- [x] 4 recipes: workbench, wood plank (building block), wood pickaxe (remake), stone pickaxe
- [x] Fixed item icons that didn't match their item (ore/wood were flat color swatches) -- they now borrow their tile's texture; tools/weapon/armor got hand-drawn vector icons instead of anonymous swatches
- [x] Tile visuals improved: ore got speckle details, workbench/trunk/planks got procedural bark/plank/tabletop details instead of a flat tint
- [x] Headless tests: registry validation, ingredient/station gating, craft transaction, refund-on-full-inventory, tree spawn/canopy shape, icon correctness

Known gap, intentionally deferred: only 4 recipes exist -- enough to prove
the system end to end. More will be added as later phases introduce things
worth crafting (weapons in Phase 4, armor in Phase 9).

## Phase 4 — Combat: DONE
- [x] Melee attack (hitbox in front of the player) and ranged attack (aimed projectile) via a weapon selected in the hotbar
- [x] Projectiles: straight-line + light gravity arc, destroyed on hitting a solid tile or an enemy, timed lifetime
- [x] Knockback (both directions) and temporary invulnerability (player + enemy i-frames)
- [x] Death and drops: enemies drop loot (rolled from `EnemyDef`) directly to the player's inventory on death
- [x] 3 enemies with distinct AI: Slime (hop), Crawler (ground patrol/chase, avoids walls and ledges), Duskwing (flying hover/chase)
- [x] Spawner: periodic, weighted by `spawn_weight`, capped at `ENEMY_MAX_ALIVE`, despawns enemies that end up far from the player
- [x] New craftable weapons/ammo so combat is actually playable: Wood Sword, Wood Bow, Arrow (all at a workbench except arrows)
- [x] Refactored Player's tile collision into `entities/tile_collision.py` so Enemy reuses it instead of duplicating it
- [x] Headless tests: AI collision probes, ledge/wall avoidance, melee/ranged damage, projectile lifecycle, contact damage/i-frames, spawner cap/despawn
- [x] Aiming polish: melee is a cone toward the mouse (not just left/right), a swing-arc visual, continuous pre-aim facing while a weapon is out, and an aim reticle
- [x] Sword balance pass (user playtest feedback): reach shortened from a spear-like 1.4 to a punchy 0.9 tiles, attack rate raised from 1.2/s to 3.0/s so swings feel responsive rather than sluggish
- [x] Duskwing balance pass (was "almost impossible to kill without taking a hit"): contact damage 10 -> 7, speed 6.5 -> 5.5, and it now backs off once within `FLYING_STANDOFF_TILES` instead of camping inside the player's hitbox dealing free contact damage every frame
- [x] Melee hit-detection generosity pass (user playtest feedback: small enemies were hard to actually connect with): reach nudged back up to 1.1 tiles, swing cone widened 110 -> 130 degrees, and small enemies (slime, duskwing) are now treated as at least `MELEE_MIN_TARGET_SIZE_TILES` (1 tile) for hit-detection purposes only -- their real collision box, movement and rendering are unchanged
- [x] Second reach increase (user playtest feedback: 1.1 tiles still felt too short): `MELEE_REACH_TILES` raised to 1.8 -- swings now reliably connect out to ~2.5 tiles from the player (measured), up from ~1.7-2

Known gaps, intentionally deferred:
- No physical dropped-item entities (loot goes straight to inventory)
- No enemy ranged attacks -- all three current enemies only deal contact damage
- `assets/20 Enemies.png` turned out to be a promotional preview image (watermarked "download all 20 enemies"), not usable art, so enemies are flat colored shapes until real sprites are added

## Equipment & UI pass (user-requested, ahead of the formal Phase 9): DONE
- [x] Real RPG-style equipment: `game/inventory/equipment.py` adds Head/Body slots; equipping moves the item out of the bag, unequipping moves it back (with a full-inventory refund guard, same pattern as crafting)
- [x] Equipped armor has a real effect: `defense` is subtracted from contact damage in combat, floored at `MIN_DAMAGE_AFTER_DEFENSE` (not just a cosmetic slot)
- [x] Two new craftable armor pieces so the equip screen isn't permanently half-empty: Wood Helmet (head, craft anywhere) and Wood Armor (body, requires a workbench) -- `leather_cap` was renamed to `wood_helmet` for thematic/tier consistency with the rest of the wood-based early game
- [x] Inventory screen redesigned as a two-panel character sheet: portrait + equipment slots + HP/Defense/Attack stats on the left, the bag grid on the right; every occupied slot (bag or equipment) is now bordered by `ItemDef.rarity`
- [x] Crafting screen redesigned: sectioned into "Craft Anywhere" / "Requires a Workbench", ingredient icons instead of text-only, hover highlighting, a ready/not-ready accent bar, and mouse-wheel scrolling (`CRAFTING_VIEWPORT_HEIGHT`) so the panel can't grow into the HUD as more recipes are added
- [x] Headless tests: equip/unequip transactions (including the full-inventory refund case), defense reducing combat damage, recipe/item registry sanity, UI slot-rect geometry (no overlaps, click hit-testing matches what's drawn), section grouping, scroll clamping

Known gaps, intentionally deferred:
- Only 2 equipment slots (Head, Body) -- more (legs, boots, accessory) can be added by extending `Equipment.SLOTS`, but there's no armor data for them yet
- Still no drag-and-drop; equip/unequip/craft are click-to-act, not click-and-drag
- The hotbar-selected weapon is *not* a separate "equipped weapon" slot in the character sheet -- it's just the current hotbar selection, mirrored as an "Attack" stat

## Health regen (user-requested): DONE
- [x] Passive regen (`PLAYER_REGEN_RATE_HP_PER_S`) while below max health, paused for `PLAYER_REGEN_DELAY_AFTER_DAMAGE_S` after any damage (contact or fall) so it can't out-heal an active fight
- [x] `Player.is_regenerating()` drives a pulsing health-bar border; F3 debug overlay shows the countdown while paused
- [x] Headless tests: heals at the correct rate, capped at max health, paused immediately after damage, resumes exactly when the delay clears, re-paused if hit again mid-regen, cleared on respawn

Known gap at the time, since resolved by the "Asset pass" below: no
food/potion healing -- `apple` was catalog-only (no "eat" action existed).

## Phase 5 — World cycle: DONE
- [x] `WorldClock` (`game/core/world_clock.py`): a real-time day length (`DAY_LENGTH_S`), a cosine ambient-light curve (no discrete day/night jump), `is_night`, and an HH:MM clock string
- [x] Sky tint follows the same ambient curve: a navy overlay peaking at midnight, a warm overlay peaking at dawn/dusk, both derived from one value so they can't drift apart
- [x] Tile-based point-light lighting (`game/world/lighting.py`): brightness = max(ambient, falloff from any nearby `TileDef.light_emit` source), searched only within the visible viewport + a margin -- never the whole world (~10ms/frame end to end with lighting + day/night active, measured)
- [x] Torch: new tile + item + recipe (wood + coal -> 3 torches, craftable anywhere), `light_emit=14`, non-solid, with a procedural stick+flame texture and a subtle flicker
- [x] Night-only enemy spawning: `SpawnTime` (ANY/DAY/NIGHT) on `EnemyDef`; Duskwing is now `NIGHT`-only (fitting, given its name) -- `EnemySpawner` filters eligible enemies by `WorldClock.is_night` before the weighted pick
- [x] Day/night HUD indicator (sun/moon icon + "Day N HH:MM"); F3 debug overlay shows day count, clock, day/night, and the raw ambient value
- [x] Fixed a rendering bug found while building this: darkening the player sprite with a plain rectangular overlay showed up as a visible box around its transparent background; switched to an RGB-only multiply blend that preserves the sprite's own alpha (enemies, being flat vector shapes, just get their fill color dimmed directly -- no such issue there)
- [x] Headless tests: clock wraparound/day-count/smoothness/is_night threshold, light falloff/radius/bounds/viewport-only search, torch tile/item/recipe, night-exclusive spawn filtering

Known gaps, intentionally deferred:
- Lighting doesn't respect occlusion (no flood-fill/shadow-casting) -- a real simplification, documented in README "How the day/night cycle and lighting work"
- Only 1 light source (Torch) and only 1 night-exclusive enemy (Duskwing) exist so far -- more of each are trivial to add via the existing data-driven registries
- Caves/underground areas use the same ambient curve as the surface (no permanent underground darkness independent of time of day) -- would need a "sky exposure" concept per column, not built yet

## Phase 6 — Biomes: DONE
- [x] Fixed-width horizontal zones (`BIOME_ZONE_WIDTH_TILES`), each independently rolling a biome via seeded weighted choice (`biome_registry.BiomeDef.zone_weight`); a fixed-radius safety window around the exact world center is always Forest so spawn is never stranded in Desert/Snow/Jungle
- [x] 4 surface biomes with their own surface/subsurface tiles: Forest (grass/dirt, unchanged), Desert (sand/sandstone), Snow (snow block/frozen dirt), Jungle (jungle grass/mud)
- [x] Per-biome deep underground: each biome has its own stone filler (`BiomeDef.underground_tile_id` -- Forest keeps plain Stone, Desert/Snow/Jungle get Desert Stone/Permafrost Stone/Jungle Stone) plus a small extra roll at a biome-exclusive gem ore (`exclusive_ore_tile_id`/`exclusive_ore_chance` -- Topaz/Sapphire/Emerald), stacked on top of the universal Coal/Iron find that still exists under every biome; caves stay identical everywhere (same noise field regardless of which biome's stone they carve out of)
- [x] Desert-exclusive vegetation: normal tree roll is replaced by cacti (1-2 tiles tall); Snow and Jungle currently reuse Forest's tree system unchanged
- [x] New material: `cactus_fiber` (mined from cacti) plus a new recipe, `arrow_cactus` (2 fiber -> 5 arrows), so desert exploration has its own resource loop
- [x] Biome-gated enemy spawning: `EnemyDef.biome_id` (None = any biome); Scorpion is the first biome-exclusive enemy (Desert only) -- `EnemySpawner` now resolves the biome at the candidate spawn column before the weighted enemy pick
- [x] F3 debug overlay shows the current biome name
- [x] Headless tests (`tests/test_phase6_biomes.py`, 24 tests): zoning determinism/seed-variation/full coverage, per-biome surface tile columns, per-biome underground stone/exclusive-gem coverage + mining one, desert no-trees/cactus-spawn/mine-for-fiber, item/recipe registry sanity, Scorpion biome gating both ways

Known gaps, intentionally deferred:
- Only 1 biome-exclusive enemy (Scorpion/Desert) -- Snow and Jungle have no exclusive enemy yet
- Hard biome borders -- zones change abruptly at their boundary, no blending/transition strip
- Caves are identical in every biome (no biome-specific cave generation, only the stone/ore they're carved out of differs)
- The three biome-exclusive gems (Topaz/Sapphire/Emerald) are catalog-only, same as `iron_ore` -- no smelting/crafting use exists for any of them yet
- Snow and Jungle have no unique surface vegetation/decoration of their own yet -- they reuse Forest's tree system as-is
- "Cave" isn't a zoned biome (see README "How biomes work") -- it's the Phase 1 universal underground, unaffected by the surface biome above it

## Asset pass (user-requested: survey every file in assets/ and put unused ones to work): DONE
- [x] Food + a real "eat" action: 8 items (`apple` plus 7 new fruits from `assets/Items/Fruits/`) get `ItemDef.heal_amount`; `Player.eat_selected()` (bound to `F`) heals and consumes one, no-op at full health or on non-food
- [x] Obtain path for food: Berry Bush (`BUSH_ID`), a new rare surface spawn in Forest/Snow/Jungle (shares Desert-exempt slot with the wooden crate) that drops one random fruit -- the first tile to need "one of several possible drops," via a new minimal `TileDef.drop_pool` field alongside the existing single-item `drop_item_id`
- [x] Two placeable interactive tiles from `assets/Traps/`, each via one new opt-in `TileDef` field so every existing tile is unaffected: Spikes (`contact_damage`, checked every frame the player overlaps a tile via `combat_system.resolve_hazard_damage`, mirroring the existing enemy contact-damage path/invulnerability window) and Trampoline (`bounce_velocity`, checked by `Player.physics_step` on landing -- launches up and skips fall damage instead of coming to rest)
- [x] New recipes: `spikes` (5 stone + 2 wood) and `trampoline` (6 wood + 3 slime_gel), both at a workbench
- [x] Headless tests (`tests/test_food_and_hazards.py`, 13 tests): eat heals/consumes/caps/no-ops (full health, non-food), bush spawn/biome-exclusion/mine-for-random-fruit, spikes damage + invulnerability window, trampoline bounce-instead-of-rest

Assets surveyed but deliberately not used this pass (see README "Known
limitations" for what stays open): the other 3 platformer characters
(MaskDude/PinkMan/VirtualGuy -- no character-select mechanic exists),
`20 Enemies.png` (a watermarked promotional image, not usable art, already
noted in Phase 4), Menu/Buttons (the pause screen is still a plain overlay;
wiring real buttons to actions like Settings would need those actions to
exist first), Checkpoints (no natural fit yet -- respawn is a fixed point,
not a placeable/activatable one), and the remaining Traps (Fan, Saw, Rock
Head, Spike Head, Falling Platforms, Sand/Mud/Ice) and Other/ particles
(Dust, Shadow, Confetti) -- each would need a new subsystem (animated
hazards, a particle system) rather than one new TileDef field, so they're
left for a future pass instead of half-implemented here.

All of the above, since implemented in "Deferred-assets pass 2" below
(user-requested: everything on this list, done properly rather than
half-implemented) -- except `20 Enemies.png`, which stays unused for the
same reason it always was (not usable art).

## Deferred-assets pass 2 (user-requested: implement everything deliberately left out of the first Asset pass): DONE
- [x] Playable character select: `game/entities/character_registry.py` registers all 4 interchangeable skins in `assets/MainCharacters/` (Ninja Frog, Mask Dude, Pink Man, Virtual Guy -- same frame size, same animation filenames); a one-time screen at startup (`GameApp.character_select_open`) lets the player click a portrait or arrow-key between them and confirm with Enter, then plays exactly as before with that skin -- `Player.character_id` is the only new field, Renderer preloads every character's animations up front and looks up the right set by id
- [x] Real pause menu: the pause overlay now has 4 working buttons (`assets/Menu/Buttons/Menu_jogo/`) instead of just a "PAUSED" label -- Resume, Settings (Zoom In/Out, Back -- real, already-existing camera controls, not fake placeholders), Restart (rebuilds the whole run from the same seed via `GameApp.restart()`/`_new_run`, kept skin), and Quit
- [x] Checkpoints (`game/world/checkpoints.py`, `tile_registry.CHECKPOINT_ID`): a craftable, placeable tile; touching one (exact-tile overlap, like Spikes) makes it the player's new respawn point and fires a Confetti burst -- unit-tested via `checkpoints.try_activate` without needing a full GameApp
- [x] A small generic particle system (`game/rendering/particles.py`): Dust (footstep puffs while running on ground) and Confetti (one-shot burst on checkpoint activation), both real source art from `assets/Other/`. The ever-present ground Shadow from the same folder is deliberately *not* a particle -- it's a persistent decal drawn directly under the player/enemies each frame, not a spawn/expire effect
- [x] Fan (`tile_registry.FAN_ID`, new opt-in `TileDef.updraft_velocity`): a placeable tile that pushes the player upward at a steady velocity while within `FAN_RANGE_TILES` above it, tapering to 0 at max range -- same "one new opt-in TileDef field" pattern as Spikes/Trampoline
- [x] Sand/Mud/Ice traps (`TRAP_SAND_ID`/`TRAP_MUD_ID`/`TRAP_ICE_ID`, new opt-in `TileDef.speed_multiplier`): placeable tiles that slow (Sand/Mud) or speed up (Ice) the player's horizontal movement while standing on them, applied in `Player.physics_step`'s ground-only horizontal move
- [x] Falling Platform (`CRUMBLE_PLATFORM_ID`): a placeable tile that crumbles to air after `FALLING_PLATFORM_TRIGGER_S` of continuous standing (any other tile, or leaving it, resets the timer) and reforms after `FALLING_PLATFORM_RESPAWN_S` -- state lives in `World` (`notify_standing_on`/`update`), not the Player, so it's independently testable
- [x] Moving hazards -- Saw, Rock Head, Spike Head (`game/world/hazard_feature.py`): each is anchored to a fixed underground position rolled deterministically at chunk-generation time (same "pure function of seed+column" guarantee as trees/ore, see `world_generator.generate_hazard_anchor`), and its current position is a sine oscillation of elapsed world time -- no per-frame mutable state, survives chunk unload/reload identically. This is a deliberate simplification of the source material (a "real" Rock Head/Spike Head charges once triggered by player proximity); these instead swing/thump on a fixed rhythm the player has to time a pass around, avoiding the need for a trigger/charge/return state machine colliding against the static tile grid
- [x] Headless tests (`tests/test_deferred_assets_pass2.py`, 25 tests): character registry/asset coverage, Fan updraft in/out of range, Sand/Mud/Ice speed multipliers (and that they don't apply mid-air), Falling Platform crumble/respawn/timer-reset, Checkpoint activation/re-activation/respawn, hazard anchor spawn coverage + oscillation math + contact damage/knockback/invulnerability, particle expiry/confetti count, new item/recipe registrations
- [x] Double jump (user follow-up: another previously-unused sprite, `double_jump.png`, exists per character): `Player.jump_count`/`PLAYER_MAX_JUMPS` allow one extra mid-air jump, reset on landing/respawn; the "double_jump" animation plays for `PLAYER_DOUBLE_JUMP_VISUAL_DURATION_S` after the *second* jump specifically (not the first), then falls back to the normal jump/fall pose -- 3 headless tests in `tests/test_phase1_smoke.py` (second jump works airborne, a third jump is a no-op, jump_count resets on landing)

Known gaps, intentionally deferred:
- Saw/Rock Head/Spike Head swing on a fixed rhythm rather than charging when the player gets close -- see the simplification note above
- The Sand/Mud/Ice traps reuse the same tinted-base-tile technique as the biome ground tiles they resemble rather than slicing `assets/Traps/Sand Mud Ice (16x6).png`, whose cell layout isn't documented anywhere in the pack (same call already made for every biome tile with no unambiguous single-cell source art)
- Fan renders as a static tile (first frame of its "on" animation) -- like Spikes/Trampoline, there's no per-tile animation state in the plain id->texture cache
- No drag-and-drop or free camera placement for hazards; Saw/Rock Head/Spike Head are environment features from world generation, not player-placeable items
- Settings only exposes Zoom (the one thing already fully working); no audio settings, since there's still no audio system (see "Cross-cutting" below)

## Crafting UX pass (user-requested: better layout, recipe discovery, a blocked-mining message, a Furnace): DONE
- [x] Crafting screen redesigned again: primary grouping is now by the result item's **category** (Building/Structures & Utility/Tools/Weapons/Armor/Ammo/Materials), a layout a player recognizes at a glance, instead of only by station; each row still carries its own station requirement as a small badge (`_station_label`) so "where do I make this" is still one glance away
- [x] Recipe discovery/unlock system: a recipe is hidden behind a "???"-style locked row until the player has *ever* obtained (mined/looted/crafted/smelted) every one of its ingredients at least once (`Player.discovered_item_ids`, permanent -- not cleared by respawn, and not the same as currently holding the item). Locked rows are specific, not mysterious: they name exactly which ingredient(s) are still undiscovered (`crafting_system.undiscovered_ingredients`) rather than hiding the recipe's name entirely. Obtaining the last missing ingredient pushes a "New recipe unlocked: X" toast (see notifications below)
- [x] On-screen notifications (`game/core/notifications.py`, a small FIFO toast queue at top-center): recipe-unlock announcements, furnace outputs ready, and -- the specifically-requested case -- trying to mine a tool-gated block without the right tool now shows "Requires a Pickaxe" instead of silently doing nothing (`Player.blocked_mining_reason`, throttled via `push_throttled` so holding the mouse button doesn't spam it every frame)
- [x] Furnace (`tile_registry.FURNACE_ID`, `game/crafting/furnace_system.py`): a craftable station where ore + Coal (fuel) becomes a bar over real time, not an instant craft -- starting a smelt consumes the ore/fuel immediately but the bar isn't granted until `smelt_time_s` passes (shown as a progress bar in the crafting screen's "Smelting" section), and a furnace can only smelt one job at a time. Resolves 4 "catalog-only" gaps called out in earlier phases: Iron Ore, Topaz, Sapphire and Emerald all now smelt into their own Bar (`game/crafting/smelt_registry.py`)
- [x] Iron Bar has a genuine use, not another dead end: Iron Pickaxe (mining_power 5.0, between Stone's 3.0 and where Phase 9's tiered materials would continue) -- Topaz/Sapphire/Emerald Bars remain catalog-only for now, same honest gap the raw gems already had
- [x] Headless tests (`tests/test_crafting_and_furnace.py`, 26 tests): discovery locking/unlocking (including the "in inventory but never discovered" edge case), `collect_and_discover`/`craft_and_discover` announcing exactly the newly-unlocked recipes, `blocked_mining_reason` for the missing-tool/right-tool/out-of-reach/no-tool-needed cases, furnace start/busy/complete/restart lifecycle including insufficient ore or fuel, and the notification queue's ordering/expiry/throttling. Plus an updated `test_phase3_crafting.py` section-layout test and a full headless GameApp smoke test (mining-blocked message -> open crafting screen -> place a furnace -> start and complete a smelt -> item granted and discovered) exercising the real Renderer draw calls, not just the underlying logic

- [x] Crafting screen redesigned a second time (user feedback: the row-based layout "looked weird" -- inconsistent full-color-fill "ready" rows next to nearly-empty locked rows, a station label floating disconnected near the icon): rebuilt as an icon grid (several recipes side by side per row, `_CATEGORY_SECTION_ORDER` sections unchanged) with a fixed details panel on the right showing whichever cell is hovered (name, station badge, full ingredient breakdown, live status line) -- shared card language (`_draw_row_card`-style accent borders) replaced with a per-cell colored border only, no more full-color fills. Undiscovered recipes no longer render at all (not even as a locked placeholder) -- `_recipe_sections`/`_crafting_layout`/`crafting_max_scroll`/`recipe_at_screen_pos` all now take `discovered_item_ids` and filter before layout, so a category with nothing discovered doesn't even show its header
- [x] Headless tests updated for the grid (`tests/test_phase3_crafting.py`): undiscovered recipes are excluded from every section, a partially-discovered recipe never appears in `_crafting_layout` or hit-tests via `recipe_at_screen_pos`, plus the existing section/scroll tests updated to the new signatures

Known gaps, intentionally deferred:
- A furnace can only run one smelt job at a time (no queue) -- placing more furnaces is the way to parallelize
- No fuel-efficiency mechanic (e.g. different fuels burning longer) -- Coal is the only fuel, one fixed quantity per smelt
- Topaz/Sapphire/Emerald Bars have no further crafting use yet (same gap Iron Bar would have had without the Iron Pickaxe)
- The "Materials" crafting-screen section is presently empty (no plain-craft recipes result in a MATERIAL item outside of smelting) -- it simply won't render until one exists, same as any other category
- With locked recipes hidden entirely, there's no in-grid hint that a whole category (e.g. Weapons) has more waiting to be discovered -- only what's already unlocked is visible, by design (see "How recipe discovery works" in README), but it does mean a player has no in-UI nudge toward what to go find next

## World-generated traps pass (user-requested: put the traps on the map): DONE
- [x] Redesigned Spikes/Fire/Arrow Trap/Falling Platform/Fan/Sand/Mud/Ice from player-craftable into world-generated environmental hazards (`TileDef.can_place=False`) -- found while exploring, not built, consistent with `assets/Traps/` being trap art rather than building-block art; Trampoline stays craftable (a bounce pad, not a hazard)
- [x] `world_generator._place_cave_hazard`: one roll per column (`CAVE_HAZARD_SPAWN_CHANCE_PER_COLUMN`) places at most one of Spikes/Fire/Arrow Trap/Falling Platform at a valid cave-floor spot (air tile, solid floor beneath, clear air above)
- [x] `world_generator._place_fan_shaft`: a rarer roll (`FAN_SHAFT_SPAWN_CHANCE_PER_COLUMN`) needing a taller find -- a floor with 4 clear tiles of air stacked above it, so the updraft has room to push the player somewhere
- [x] `world_generator._surface_tile_for`: each biome's surface row occasionally swaps for that biome's own surface trap (Desert -> Loose Sand, Snow -> Slick Ice, Jungle -> Sticky Mud, `SURFACE_TRAP_SPAWN_CHANCE_PER_COLUMN`) -- Forest has no entry in `_BIOME_SURFACE_TRAP_TILE`, so the always-Forest spawn window stays hazard-free
- [x] Fixed a crash left over from an unfinished prior session: `generate_column` called an undefined `_surface_tile_for`, so **every** column generation raised `NameError` -- 76 of 200 tests were failing before this pass
- [x] Updated stale tests from the earlier craftable-traps design (recipe/item registration assertions for spikes/falling_platform/fan/trap_mud/trap_ice) and widened the per-biome underground-tile-set assertions to allow the newly-legitimate cave hazard/fan tile ids
- [x] Headless tests (`tests/test_world_generator_second_pass_traps.py`): regression test that `generate_column` doesn't crash, cave hazards/fan shafts spawn in a wide scan with correct floor/clearance geometry, biome surface traps spawn in Desert/Snow/Jungle and never in Forest
- [x] Fixed a second unfinished-refactor bug found while testing this pass: `hazard_feature.SPIKED_BALL` (a 4th moving-hazard kind, already spawned in world gen and dealing contact damage) had no entry in `assets.load_hazard_textures`, so `Renderer._draw_hazard_sprite` crashed with `KeyError('spiked_ball')` the first time one was ever drawn -- wired up its real source art (`assets/Traps/Spiked Ball/Spiked Ball.png`) and added a regression test asserting every `hazard_feature.ALL_KINDS` entry has a texture

## Underground darkness (user-requested: caves/underground should actually be dark): DONE
- [x] `lighting.ambient_light_for_depth(depth_below_surface, sky_ambient)`: the day/night sky ambient now fades out below the surface, floored at `UNDERGROUND_MIN_AMBIENT` over `UNDERGROUND_DARK_DEPTH_TILES`, independent of time of day -- previously a cave at noon was exactly as bright as the open sky, so a Torch's light contribution was invisible until night
- [x] `World.surface_height_at(x)` (small refactor: `surface_spawn_y` now calls it instead of duplicating the `surface_height` import/call)
- [x] `Renderer._draw_world/_draw_player/_draw_enemies` each compute their own local ambient from depth before calling `lighting.light_level_at` (tiles per-column, entities per-position) -- everything below the surface fades toward near-black regardless of hour, and Torches/Fire matter down there exactly like they already did on the surface at night
- [x] Headless tests (`tests/test_phase5_world_cycle.py`): ambient unchanged at/above the surface, fades out underground even at noon, floored (never pitch black) even at midnight, `World.surface_height_at` matches the existing `surface_spawn_y`

Known gap, intentionally deferred: the darkness falloff is purely depth-based (distance below the fixed surface line), not true line-of-sight/occlusion -- a shallow open pit and an enclosed cave at the same depth get the same ambient, consistent with the lighting system's existing "no occlusion" simplification (see README "How the day/night cycle and lighting work").

## Phase 7 — Procedural structures + Save/Load: DONE
- [x] Chest (`tile_registry.CHEST_ID`): a lootable tile found only inside structures (not player-craftable/placeable, same as the world-generated traps), texture reused from `assets/Items/Boxes/Box2` (same pack as the wooden crate's Box1, previously unused). Reuses the existing `drop_pool` mechanism (Bush's "one of several possible drops") for its loot instead of a new loot-table system, drawing from already-registered valuable items (`iron_bar`, `topaz`, `sapphire`, `emerald`, `iron_pickaxe`, `wood_sword`, `wood_helmet`) -- no new items needed
- [x] `game/world/structures.py`: procedural structure placement, mirroring the tree-slot pattern (`world_generator._tree_center_for_slot`/`_tree_role_at`) at a much coarser slot width (`STRUCTURE_SLOT_WIDTH_TILES`) since structures are rarer/bigger -- a pure function of `(seed, slot_index)`, independent of which column asks, same determinism guarantee as everything else in world generation
- [x] Three structure kinds, each a hand-built 7-wide blueprint: **House** (surface, Wood Plank floor/walls/roof, doorway, Torch, Chest, Workbench -- worth walking into), **Ruins** (surface, Stone, no roof, each wall tile independently has `RUINS_WALL_COLLAPSE_CHANCE` of being left out so nature/terrain shows through the gaps, still guarantees a walkable interior + Chest), **Underground Room** (forcibly carved out of rock regardless of what was there -- walls/ceiling built from that column's own biome `underground_tile_id` so a Desert room reads as Desert Stone, not generic Stone; Wood Plank floor, Torch, Chest)
- [x] "Respecting terrain": a House/Ruins placement is skipped (rerolls to nothing) if the surface height varies more than `STRUCTURE_MAX_TERRAIN_VARIANCE_TILES` across its footprint, so nothing visibly floats over a cliff or gap
- [x] `structures.place_structures` runs last in `generate_column` (after cave hazards/fan shafts), so a structure's carve/overwrite always wins -- same last-applied-wins layering already used for decoration -> hazards -> fan shafts. `STRUCTURE_MARGIN_TILES` guarantees neighboring slots' footprints can never overlap
- [x] Headless tests (`tests/test_phase7_structures.py`): every kind spawns in a wide deterministic scan, no two structures overlap, every blueprint offset actually lands correctly through `generate_column` (real integration, not just the blueprint dict), House/Ruins floor sits at that column's own `surface_height`, the Chest is always reachable (solid floor beneath, open air above), Underground Room interior is genuinely hollowed out, and Underground Room walls use the correct per-biome stone (regression test for an early version that hardcoded generic Stone and broke the Phase 6 biome-purity tests)
- [x] `game/core/save_system.py`: pure `serialize`/`deserialize` (seed, `world.elapsed_s`, world clock, full player state including inventory/equipment/discovered items, in-progress furnace jobs, and **only modified chunks** -- diffed tile-by-tile against a freshly recomputed procedural baseline via `generate_column`, not saved whole) plus thin `save_to_file`/`load_from_file`/`save_exists` file wrappers, single slot (`SAVE_FILE_PATH` = `saves/save.json`, gitignored)
- [x] Two new pause-menu buttons, Save and Load (`GameApp.save_game`/`load_game`, wired through `InputHandler._handle_pause_click` exactly like the existing Restart button) -- hand-drawn floppy-disk/down-arrow icons since no Save/Load art exists in the pack, same precedent as the tool/weapon icons
- [x] Headless tests (`tests/test_phase7_save_load.py`): round-trip of player state/furnace jobs through `serialize`/`deserialize`, only dirty chunks are ever saved, a modified tile round-trips exactly and the rest of its chunk still matches the procedural baseline, real file round-trip via a temp path, missing-file load returns `None`, and a full end-to-end test through the actual pause-menu click path (`InputHandler` -> `GameApp`), not just the underlying functions

Known gaps, intentionally deferred:
- Tower is not implemented -- the game has no ladder/climbing mechanic (only single + double jump), so a tall vertical structure's loot would be unreachable; revisit once/if a climbing mechanic exists
- Structure terrain-matching is a variance check across the footprint, not true terrain-carving/leveling -- an extreme edge case simply skips placement (rerolls to nothing) rather than adapting the shape
- Save is single-slot -- no multiple save files or a picker UI
- Enemies, projectiles, particles, and on-screen notifications are not persisted -- they're transient/regenerable, same as what already happens after Restart
- Structure placement doesn't actively avoid the biome-surface-trap or moving-hazard-anchor systems when choosing a spot -- low collision probability, not engineered around (same reasoning already applied to e.g. trees vs. cave hazards)

## Inventory tooltip + right-click quick actions (user-requested): DONE
- [x] Hovering any occupied bag or equipment slot (while the inventory screen is open) shows a floating tooltip next to the cursor (`Renderer._draw_item_tooltip`): name colored by rarity, category/rarity line, wrapped `ItemDef.description`, and a category-specific stat block (`_item_tooltip_stat_lines` -- mining power for tools, damage + melee/ranged for weapons, defense/slot for armor, heal amount for food, durability/value where set). Clamped so it never overflows the window even hovering a slot in the corner
- [x] Right-clicking a bag item (`InputHandler._handle_inventory_right_click`): armor equips immediately (same transaction the existing left-click path already uses); anything else swaps places with whatever's in the *currently selected* hotbar slot via a new `Inventory.swap_slots(a, b)` -- a fast way to load the hotbar without dragging. Equipment slots aren't a right-click target (unequip already has its own left-click action)
- [x] Headless tests: `Inventory.swap_slots` (exchange, into-an-empty-slot, self-swap no-op) in `tests/test_phase1_smoke.py`; right-click equip/hotbar-swap/empty-slot-no-op, `_hovered_inventory_item` for bag/equipment/nothing, `_item_tooltip_stat_lines` varying by category, and a real `_draw_item_tooltip` render (including a stay-on-screen check near a window corner) in `tests/test_equipment.py`

## Summoner class (first character class, user-requested): DONE
- [x] `game/entities/class_registry.py` (`ClassDef`, same `_register`/`get`/`all_classes()` pattern as `character_registry.py`): two classes, **Warrior** (`allowed_weapon_classes=("normal",)`, reproduces exactly today's combat since every existing weapon defaults to `ItemDef.weapon_class="normal"`) and **Summoner** (`allowed_weapon_classes=("summon",)`, starts with a Twig Rod)
- [x] A second start-of-run select screen (`GameApp.class_select_open`), shown right after the existing character-skin picker closes -- same boolean-gate/`InputHandler`-event/`Renderer`-screen pattern as character select, but text cards (no per-class art exists) instead of portraits
- [x] `ItemDef` gained two additive fields (`weapon_class`, `summons_id`) so no existing item registration needed to change; `combat_system.try_attack` gates every attack on `item_def.weapon_class in class_def.allowed_weapon_classes` before dispatching to melee/ranged/summon, and surfaces a `Player.blocked_weapon_class_reason()` toast (mirrors `blocked_mining_reason`) when a class can't use the selected item
- [x] Two summon rods (`game/items/item_registry.py`), craftable like any other weapon (`recipe_registry.py`): **Twig Rod** (`wood x8`, anywhere -- also the Summoner's free starting item) summons a weak **Twig Sprite**; **Iron Rod** (`iron_bar x3, wood x5, slime_gel x2`, workbench) summons a much stronger **Iron Guardian** -- a second use for Iron Bar besides the Iron Pickaxe. Both land in the crafting screen's existing "Weapons" section with zero renderer changes
- [x] New `Summon`/`SummonDef`/`summon_ai.py` triple (`game/entities/`), mirroring the `Enemy`/`EnemyDef`/`enemy_ai.py` split: casting a rod (re)summons its minion at the player's position, replacing any currently active one -- only one summon is active at a time. `summon_ai.update` seeks the nearest alive enemy within `seek_radius_tiles` and flies at it, otherwise hovers near the player (snapping back if it strays past `follow_distance_tiles`); `combat_system.resolve_summon_attacks` deals the actual damage tick once in `attack_range_tiles`, keeping the same "AI moves, combat_system damages" split enemies already use
- [x] `player.class_id` round-trips through `save_system` (old saves without the field default to Warrior); `GameApp.restart()` carries `class_id` through and re-grants the class's starting item, same as it already carries `character_id`
- [x] Headless tests (`tests/test_summoner_class.py`, 17 tests): registry sanity, `blocked_weapon_class_reason` for every class/weapon combination, `try_attack`'s class gate both ways (including that a blocked melee swing lands no damage), casting-then-replacing a summon through the real `InputHandler` click path, `summon_ai` chasing/damaging a nearby enemy and hovering near the player with none around, the class-select screen's click+confirm path granting the starting item, and a full `GameApp` boot through both select screens ending with an active summon
- [x] Manually verified in the real (headless-SDL) renderer: the class-select screen, the Twig Rod's procedural icon in the inventory/hotbar, the crafting screen's Weapons section (Iron Rod correctly shows "not ready" without a nearby workbench, exactly like Stone Pickaxe/Wood Armor already did), and a live Twig Sprite flying to and damaging a nearby enemy

Known gaps, intentionally deferred:
- Only 2 classes (Warrior, Summoner) and 2 summon tiers -- proves the system end to end rather than building a full progression ladder in one pass
- Summons cannot take damage in this pass -- no enemy ever targets them (there's no "enemy attacks a friendly entity" combat path anywhere in the game yet); revisit if summons feel too safe
- Summons move flying-style (gravity ignored, no wall/ledge avoidance) -- the same deliberate simplification `enemy_ai._update_fly` already uses for Duskwing, needed here so a minion can follow the player anywhere (caves, gaps, mid-air) without ground-pathing AI
- No HUD indicator for the active summon (name, or a health bar if summons ever become damageable)
- A class restricts *attacking*, not *selecting* -- a disallowed weapon can still sit in the hotbar and be "held" (pre-aim facing still works), the attack itself is just a no-op with a toast

## RPG skill/leveling system (user-requested: character skills, leveling, magic level, defenses, XP): DONE
- [x] New `game/skills/` package (a subsystem alongside `game/combat/`, `game/crafting/`, `game/inventory/`): six independent RuneScape-style skills -- **Attack, Defense, Magic, Mining, Crafting, Hitpoints** -- each with its own XP bar and level, using the real RuneScape level-1-99 XP curve (`game/skills/xp_table.py`, `xp(99) = 13,034,431`, verified against the well-known reference values)
- [x] `game/skills/skills.py`'s `Skills` (one per `Player`, mirrors `Equipment`'s role): `add_xp` queues every level crossed onto `pending_level_ups` rather than pushing notifications itself, so XP-granting call sites (combat/mining/crafting) don't need to know about the UI -- `GameApp.step()` drains the queue once a frame and pushes a toast via the existing `NotificationQueue`, the same "New recipe unlocked" mechanism already used elsewhere
- [x] A 15-node skill-point tree (`game/skills/skill_tree_registry.py`, `SkillNodeDef`, same `_register`/`get` registry pattern as everything else): 3 tiers per skill (Attack/Defense/Magic/Mining/Crafting; Hitpoints has none) at levels 10/30/50, unlocked by spending points earned 1-per-level -- `Skills.available_points` is derived from `level - 1 - unlocked_count`, not a separately stored counter, so it can't desync from saved state. Tiers 2 and 3 also require the previous tier's node specifically (`SkillNodeDef.requires_node_id`), a real chain rather than just a level gate, so it reads as a tree to climb, not a flat list
- [x] Every skill has a real, wired-in effect: **Attack** boosts melee/ranged damage dealt (level curve + `attack_keen_edge`/`attack_berserker`/`attack_deadly_precision` nodes); **Defense** adds a flat bonus on top of equipment defense via a new shared `combat_system.player_total_defense(player)` helper (deduplicating 3 previously-copy-pasted `player.equipment.total_defense()` reads); **Magic** boosts the Summoner's summon damage, baked into the summon's per-instance stats at cast time (`Summon.damage`/`move_speed`/`attack_interval_s` now diverge from their `SummonDef`, the same way `Enemy.health` already diverges from `enemy_def.max_health`); **Mining** boosts mining power and (with `mining_deep_delver`) mine tick speed; **Crafting** boosts its own XP gain (`crafting_master`/`crafting_artisan`) and can refund an ingredient stack (`crafting_resourceful`, 15% chance); **Hitpoints** raises `player.max_health` on level-up (and heals by the same amount) and passively gains 1/3 of every Attack/Defense/Magic XP grant, the real RuneScape mechanic where every combat skill also trains survivability
- [x] XP hooks live inside the function that already owns the relevant transaction (no new call sites elsewhere): landed melee/ranged hits and kills in `combat_system._try_melee_attack`/`update_projectiles` (both gained a `player` parameter), summon hits in `resolve_summon_attacks` (also gained `player`), damage taken in `resolve_contact_damage`/`resolve_hazard_damage`/`resolve_hazard_feature_damage`, tile breaks in `Player.try_mine`, and successful crafts/smelts in `crafting_system.craft_and_discover`/`GameApp._update_furnace`
- [x] New "Skills" screen (`K`, joins the E/C/K mutual-exclusion group): a 6-row skill list with level + XP progress bar (left, same bar-fill technique as the health bar) and the selected skill's 3-node tree (right) -- nodes stacked vertically and connected by a line (gold once unlocked through, grey otherwise) so it visually reads as a tree, locked/unlockable/unlocked border colors, and a "Requires X first" reason shown when the level is high enough but the prior tier isn't unlocked yet
- [x] Character sheet (inventory screen, `E`) expanded into a real "at a glance" summary: the existing HP/Defense/Attack/Combat Lv block now sits above a compact 2-column, 6-entry skill-level grid (`_draw_skills_summary`) -- full per-skill XP bars and the tree itself still live in the Skills screen, this is just the summary
- [x] A new always-on top-left HUD bar (`_draw_combat_level_bar`, user-requested "barra no topo com o nível/%"): `Combat Lv N` plus a % progress bar (`Skills.combat_level_progress_ratio`, the average of Attack/Defense/Magic/Hitpoints' individual progress-to-next-level, since Combat Lv itself has no XP track of its own) -- wrapped in its own translucent panel, same technique as the existing top-center notification banner, so the white text stays readable regardless of sky color or bar fill
- [x] XP gain rates increased ~1.5x across the board (user feedback: leveling felt too slow) -- both the flat per-action XP amounts and the per-level passive stat percentages in `game/settings.py`
- [x] `player.skills` (xp + unlocked nodes per skill) round-trips through `save_system` (old saves without the field default to 0 xp / no nodes)
- [x] Headless tests (`tests/test_skills.py`, 36 tests, plus updates to `tests/test_phase4_combat.py`/`tests/test_summoner_class.py`/`tests/test_food_and_hazards.py`/`tests/test_phase7_save_load.py` for the new `player_total_defense` formula and the two combat_system signature changes): XP table reference values and monotonicity, `add_xp`/`drain_level_ups` single- and multi-level-up queuing, skill-tree registry sanity (including the tier-chain shape), `try_unlock_node` gating (level, points, already-unlocked, and the new prerequisite-tier check), every multiplier/bonus helper at baseline and with nodes, `level_progress_ratio`/`combat_level_progress_ratio`, every XP hook point (melee/ranged/summon/defense/mining/crafting/smelt), the Magic-boosted summon-damage-at-cast-time behavior, the `crafting_resourceful` refund roll, and a full `GameApp` test driving real level-up notifications and the Skills screen's click-to-select/click-to-unlock flow through the real `InputHandler`
- [x] Manually verified in the real (headless-SDL) renderer: the always-on top-left Combat Lv bar during normal gameplay, the Skills screen's connected 3-node vertical tree (unlocked chain in gold, an unlockable tier-3 node in green), and the character sheet's new skills summary grid -- no layout overlap anywhere

Known gaps, intentionally deferred:
- No Ranged/Strength split (Attack alone covers all weapon damage) -- there's no hit-chance/accuracy system in this game to hang a RuneScape-authentic Attack-vs-Strength split on
- XP amounts are flat per action (mining/crafting don't scale by tile tier or recipe complexity yet) -- easy constants to retune later, not a structural limitation
- No skill-tree respec -- points, once spent, stay spent
- No HUD element for individual XP-gain popups ("+12 Attack XP") -- the top bar shows aggregate Combat Lv progress and the level-up toast fires on an actual level-up, but there's no per-hit XP number floating up yet

## Phase 8 — NPCs
- [ ] Merchant, blacksmith, guide: dialogue, shop inventory, spawn conditions

## Phase 9 — Progression
- [ ] Tiered materials (wood -> stone -> iron -> steel -> magic) unlocking new tools/gear/mechanics, not just bigger numbers
- [ ] More equipment slots (legs, boots, accessory) and higher armor tiers -- the equip system and UI already support this, see "Equipment & UI pass" above

## Phase 10 — Bosses
- [ ] First original boss: health bar, phases, distinct attack patterns, summon condition, exclusive drops

## Cross-cutting (ongoing, not a phase)
- [ ] Audio architecture (music/sfx hooks) — not blocking on final audio assets
- [ ] Debug tools beyond F3 overlay: give-item, teleport, spawn-enemy, regen-world commands
- [ ] Configurable input bindings
