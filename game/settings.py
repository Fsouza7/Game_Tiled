"""Central configuration for the sandbox game. No magic numbers elsewhere."""
import os

# --- Window ---
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 768
FPS = 60
WINDOW_TITLE = "Sandbox Prototype"

# --- Audio ---
# These two are only the *defaults* a fresh install starts at -- the live,
# user-adjustable values are held on GameApp.prefs (game/core/settings_store.py)
# and persisted to SETTINGS_FILE_PATH, independent of any save slot (see
# that module's docstring for why: preferences should survive even with
# no save yet, and a Restart/Load shouldn't touch how loud the player set
# things).
MUSIC_VOLUME = 0.4
SFX_VOLUME = 0.7
VOLUME_STEP = 0.1
SETTINGS_FILE_PATH = os.path.join("saves", "settings.json")

# --- World / Tiles ---
TILE_SIZE = 32
CHUNK_WIDTH = 32  # tiles per chunk (columns)
WORLD_WIDTH_CHUNKS = 128
WORLD_WIDTH_TILES = CHUNK_WIDTH * WORLD_WIDTH_CHUNKS
WORLD_HEIGHT_TILES = 150
BEDROCK_ROWS = 3  # bottom rows that are indestructible (world floor limit)

# How many chunks around the player must exist (loaded) at any time.
CHUNK_LOAD_RADIUS = 3
# Chunks further than this from the player are unloaded to free memory.
CHUNK_UNLOAD_RADIUS = 6

# --- World generation ---
DEFAULT_SEED = int(os.environ.get("SANDBOX_SEED", "84739291"))
SURFACE_BASE_HEIGHT = 45  # average row index (from top) of the grass surface
SURFACE_AMPLITUDE_1 = 6
SURFACE_AMPLITUDE_2 = 3
DIRT_LAYER_MIN = 4
DIRT_LAYER_MAX = 8
CAVE_THRESHOLD = 0.72  # higher = fewer caves
CAVE_MIN_DEPTH_BELOW_SURFACE = 6  # protects terrain right under the surface
ORE_MIN_DEPTH_BELOW_SURFACE = 8

# --- Biomes ---
# The world is split into fixed-width horizontal zones; each independently
# (and deterministically) rolls a biome, except the zone containing the
# world's exact center, which is always Forest -- guaranteeing the fixed
# spawn point always lands somewhere temperate. See world_generator.biome_at.
BIOME_ZONE_WIDTH_TILES = 350
CACTUS_SPAWN_CHANCE = 0.10  # per column, desert-only (replaces the tree roll)
CACTUS_TALL_CHANCE = 0.5  # chance a spawned cactus is 2 tiles instead of 1

# --- Physics ---
GRAVITY = 0.7  # px/frame^2
MAX_FALL_SPEED = 22.0
PLAYER_MOVE_SPEED = 5.5
PLAYER_JUMP_VELOCITY = -14.0
PLAYER_MAX_JUMPS = 2  # 2 = one double jump; jump_count resets to 0 on landing
PLAYER_DOUBLE_JUMP_VELOCITY = -14.0  # same punch as the first jump (Celeste-style consistency)
FALL_DAMAGE_MIN_SPEED = 16.0  # vertical speed above which landing hurts
FALL_DAMAGE_PER_UNIT = 4.0  # hp lost per unit of speed above the threshold

# --- Player ---
PLAYER_WIDTH_TILES = 0.8
PLAYER_HEIGHT_TILES = 1.8
PLAYER_MAX_HEALTH = 100
PLAYER_REACH_TILES = 6.0
PLAYER_PLACE_COOLDOWN_S = 0.15
# One "hit" of mining_power is applied every this many seconds while the
# mine button is held (see Player.try_mine) -- the real lever on how much
# a block resists being mined, since ticks-to-break = ceil(resistance /
# mining_power) regardless of this value. At the old 0.05s, even a bare
# hand cleared dirt in a single, imperceptible tick and the wood->stone->
# iron->steel->arcane pickaxe ladder made almost no felt difference on
# everyday blocks. 0.2s keeps digging brisk (a plain dirt/stone block is
# still 1-2 ticks) while giving the tool tier a real, feelable payoff on
# tougher tool-gated material (ore/gems can take several ticks with the
# starter pickaxe, one tick with a late-game one).
PLAYER_MINE_TICK_S = 0.2

# --- Grapple Hook (accessory slot) ---
GRAPPLE_MAX_RANGE_TILES = 7.0
GRAPPLE_STEP_TILES = 0.25  # raycast step size when searching for a wall to catch
GRAPPLE_PULL_SPEED = 11.0  # px/frame toward the anchor, same frame-based scale as PLAYER_MOVE_SPEED
GRAPPLE_ARRIVAL_DISTANCE_TILES = 0.5
GRAPPLE_COOLDOWN_S = 0.4

# --- Health regeneration ---
PLAYER_REGEN_RATE_HP_PER_S = 2.5
# Any damage (contact, fall) resets this timer; regen only resumes once it
# runs out, so tanking hits in a fight can't out-heal itself.
PLAYER_REGEN_DELAY_AFTER_DAMAGE_S = 5.0

# --- Camera ---
CAMERA_SMOOTHING = 0.12  # 0..1, higher = snappier follow
CAMERA_DEFAULT_ZOOM = 1.0
CAMERA_MIN_ZOOM = 0.5
CAMERA_MAX_ZOOM = 2.0
CAMERA_ZOOM_STEP = 0.1
# Screen shake on the player taking damage (see Camera.shake) -- scaled by
# the hit's own damage amount so a Duskwing peck barely nudges the screen
# but the Slime King's stomp reads as a real jolt, without needing a
# separate "this one's special" signal from combat_system.
CAMERA_HIT_SHAKE_DURATION_S = 0.15
CAMERA_HIT_SHAKE_PX_PER_DAMAGE = 0.3
CAMERA_HIT_SHAKE_MAX_PX = 7.0

# --- Rendering ---
PLAYER_ANIMATION_FRAME_DELAY = 4  # render-frames per animation frame
# Per-layer horizontal scroll speed for the layered parallax background
# (see assets.BACKGROUND_LAYER_PATHS / Renderer._draw_background), back to
# front: sky barely moves (it's just a backdrop gradient), each silhouette
# layer scrolls a bit faster than the one behind it for a depth cue, capped
# well below 1.0 (full world speed) since these are meant to read as
# distant scenery, not part of the playable foreground.
BACKGROUND_LAYER_PARALLAX = {
    "sky": 0.0,
    "clouds": 0.1,
    "rock_mountains": 0.25,
    "grass_mountains": 0.45,
}
# How long the "double_jump" animation shows before falling back to the
# regular jump/fall pose -- purely cosmetic, doesn't affect physics.
PLAYER_DOUBLE_JUMP_VISUAL_DURATION_S = 0.35

# --- Crafting ---
STATION_SEARCH_RADIUS_TILES = 4

# --- Combat ---
# Note: like GRAVITY/PLAYER_MOVE_SPEED above, these are px/frame (added
# directly each game-loop tick, not scaled by dt) to match how Player/Enemy
# physics already works -- not tiles/second.
PLAYER_HIT_INVULNERABILITY_S = 0.8
MIN_DAMAGE_AFTER_DEFENSE = 1.0  # armor can reduce damage but never to zero
ENEMY_HIT_INVULNERABILITY_S = 0.15
MELEE_REACH_TILES = 1.8  # generous sword range (user feedback: 1.1 still felt too short)
MELEE_ARC_DEGREES = 130.0  # total swing cone width, centered on the aim direction
MELEE_SWING_VISUAL_DURATION_S = 0.18
# Small/fast enemies (slime, duskwing) are treated as at least this big when
# checking whether a swing connects, so their small sprite size doesn't
# make them frustratingly hard to actually hit -- this only affects melee
# hit detection, not their real collision box, movement, or rendering.
MELEE_MIN_TARGET_SIZE_TILES = 1.0
KNOCKBACK_SPEED = 6.0
KNOCKBACK_UPWARD_SPEED = 8.0
PROJECTILE_SPEED = 16.0
PROJECTILE_GRAVITY_SCALE = 0.25  # fraction of world GRAVITY applied to arrows
PROJECTILE_LIFETIME_S = 3.0
PROJECTILE_SIZE_TILES = 0.3

# --- Enemies ---
# Population cap and spawn cadence both now depend on where/when the
# player is (see EnemySpawner._current_limits): fewer, slower spawns in
# daylight at the surface; more, faster ones at night; underground is the
# most dangerous of all, at any hour, since caves are already dark
# regardless of the surface day/night cycle (see "How lighting works").
ENEMY_MAX_ALIVE_DAY = 5
ENEMY_MAX_ALIVE_NIGHT = 10
ENEMY_MAX_ALIVE_UNDERGROUND = 14
ENEMY_SPAWN_INTERVAL_DAY_S = 5.0
ENEMY_SPAWN_INTERVAL_NIGHT_S = 3.0
ENEMY_SPAWN_INTERVAL_UNDERGROUND_S = 2.0
# How far below the surface (in tiles) the player has to be before spawns
# switch to the underground rules -- a few tiles of slack so walking
# through a shallow dip in the terrain doesn't toggle it.
UNDERGROUND_SPAWN_DEPTH_TILES = 4
ENEMY_SPAWN_MIN_DISTANCE_TILES = 18
ENEMY_SPAWN_MAX_DISTANCE_TILES = 32
ENEMY_CHASE_RADIUS_TILES = 10
ENEMY_DESPAWN_DISTANCE_TILES = 60  # cull enemies that end up far from the player
SLIME_HOP_IMPULSE = 10.0
SLIME_HOP_INTERVAL_MIN_S = 0.7
SLIME_HOP_INTERVAL_MAX_S = 1.6
FLYING_BOB_AMPLITUDE_TILES = 0.4
FLYING_BOB_FREQUENCY = 2.0
FLYING_SPAWN_HEIGHT_TILES = 5  # hover altitude above the grass, not perched on it
# Once within this range while chasing, a flyer backs off instead of
# camping directly on top of the player -- otherwise it deals contact
# damage on nearly every frame it's in melee range, with no way to avoid it.
FLYING_STANDOFF_TILES = 1.6

# --- Summons (Summoner class) ---
SUMMON_BOB_AMPLITUDE_TILES = 0.3
SUMMON_BOB_FREQUENCY = 3.0
SUMMON_HOVER_HEIGHT_TILES = 1.2  # idle altitude above the player's center

# --- Skills (RPG leveling -- Attack/Defense/Magic/Mining/Crafting/Hitpoints) ---
# XP granted per action -- easy to retune later, same "pick a reasonable
# number, document it, adjust from playtesting" approach already used for
# e.g. MELEE_REACH_TILES's tuning passes. Bumped ~1.5x (user feedback:
# leveling felt too slow) from the first pass's values.
ATTACK_XP_PER_DAMAGE = 1.5
ATTACK_KILL_BONUS_XP = 25.0
DEFENSE_XP_PER_DAMAGE_TAKEN = 1.5
MAGIC_XP_PER_DAMAGE = 2.25
MINING_XP_PER_BREAK = 8.0
CRAFTING_XP_PER_CRAFT = 12.0
CRAFTING_XP_PER_SMELT = 9.0
# A fraction of every Attack/Defense/Magic XP grant also goes to
# Hitpoints, same as real RuneScape -- every combat skill trains survivability.
HITPOINTS_XP_SHARE = 1.0 / 3.0
HITPOINTS_HP_PER_LEVEL = 10.0
# Per-level passive multipliers/bonuses (stack with the skill's tree nodes).
# `(level - 1)` so level 1 is a true 1.0x / 0-flat baseline and each
# level-up is a chunk you can actually see (user playtest: 0.75%/0.9%
# per level vanished into rounding on the floating damage numbers, and
# +1 HP didn't register as a bigger health bar).
ATTACK_DAMAGE_PCT_PER_LEVEL = 0.05
MAGIC_DAMAGE_PCT_PER_LEVEL = 0.08
MINING_POWER_PCT_PER_LEVEL = 0.015
DEFENSE_FLAT_PER_LEVEL = 0.3
CRAFTING_RESOURCEFUL_CHANCE = 0.15

# --- Hazards / interactive tiles ---
SPIKES_CONTACT_DAMAGE = 12.0
# Big enough to feel like a real launch, not just a stronger jump.
TRAMPOLINE_BOUNCE_VELOCITY = 24.0

# --- Inventory ---
INVENTORY_SLOTS = 20
HOTBAR_SLOTS = 9
DEFAULT_STACK_SIZE = 99
# Shared stash accessed from any placed Personal Chest (piggy-bank /
# ender-chest style -- contents follow the player, not the tile).
PERSONAL_CHEST_SLOTS = 20
# World-generated loot Chest (found in structures -- Houses, Ruins,
# Underground Rooms): each one gets its own small, one-time random loot
# roll instead of a shared stash. See game/world/loot_chest.py.
LOOT_CHEST_SLOTS = 10
LOOT_CHEST_MIN_ROLLS = 2
LOOT_CHEST_MAX_ROLLS = 4

# --- Map (fog-of-war, M to open) ---
# The world is divided into MAP_CELL_SIZE_TILES x MAP_CELL_SIZE_TILES
# cells; a cell is "explored" (and gets a fixed representative color,
# sampled once) the first time the player comes within
# MAP_REVEAL_RADIUS_TILES of it. See game/world/exploration.py.
MAP_CELL_SIZE_TILES = 8
MAP_REVEAL_RADIUS_TILES = 40

# --- World clock (day/night) ---
DAY_LENGTH_S = 600.0  # one full day+night cycle, real seconds
DAY_MAX_AMBIENT = 1.0  # ambient light at noon
NIGHT_MIN_AMBIENT = 0.12  # ambient light at midnight -- dim, not pitch black
NIGHT_LIGHT_THRESHOLD = 0.5  # ambient below this counts as "night" for spawning
# Sleeping in a Bed (see game/world/beds.py) skips straight to this point
# in the cycle -- same "mid-morning" fraction __init__ already starts a
# fresh run at, so waking up always lands at the same time of day.
MORNING_TIME_OF_DAY_FRACTION = 0.3

# --- Lighting ---
# Torch light is computed only for the visible viewport (+ this margin) each
# frame, not the whole world -- see game/world/lighting.py.
LIGHT_RADIUS_TILES = 7.0  # max reach of a full-strength (light_emit=15) source
LIGHT_SEARCH_MARGIN_TILES = 8  # >= LIGHT_RADIUS_TILES so no visible source is missed
MAX_DARKNESS_ALPHA = 195  # 0-255, how dark an unlit tile gets at full night

# Sky ambient light (the day/night curve above) fades out below the
# surface, independent of time of day -- so caves/underground are
# genuinely dark and torches/Fire actually matter down there even at
# noon, not just at night. See game/world/lighting.py ambient_light_for_depth.
UNDERGROUND_DARK_DEPTH_TILES = 10.0  # fully faded out this many tiles below the surface
UNDERGROUND_MIN_AMBIENT = 0.04  # never fully pitch black, same reasoning as NIGHT_MIN_AMBIENT
TORCH_FLICKER_AMPLITUDE = 0.06
TORCH_FLICKER_SPEED = 9.0

# --- Playable characters ---
CHARACTER_PORTRAIT_SIZE = 96

# --- Terrain speed-modifier traps (Sand/Mud/Ice) ---
TRAP_SAND_SPEED_MULTIPLIER = 0.7
TRAP_MUD_SPEED_MULTIPLIER = 0.45
TRAP_ICE_SPEED_MULTIPLIER = 1.35  # faster, not frictionless -- see README simplification note

# --- Fan (updraft) ---
FAN_UPDRAFT_VELOCITY = 9.0  # px/tick upward push at zero distance, tapering to 0 at FAN_RANGE_TILES
FAN_RANGE_TILES = 3.0

# --- Falling platforms ---
FALLING_PLATFORM_TRIGGER_S = 0.5  # continuous standing time before it crumbles
FALLING_PLATFORM_RESPAWN_S = 4.0

# --- Moving hazard features (Saw, Rock Head, Spike Head, Spiked Ball) ---
# Each is anchored to a fixed world position rolled deterministically during
# chunk generation; its current position is a pure function of elapsed world
# time (amplitude/period), not a triggered charge -- see
# game/world/hazard_feature.py for why.
HAZARD_SPAWN_CHANCE_PER_COLUMN = 0.012
HAZARD_MIN_DEPTH_BELOW_SURFACE_TILES = 10
SAW_CONTACT_DAMAGE = 18.0
SAW_AMPLITUDE_TILES = 2.2
SAW_PERIOD_S = 3.2
ROCK_HEAD_CONTACT_DAMAGE = 20.0
ROCK_HEAD_AMPLITUDE_TILES = 0.7
ROCK_HEAD_PERIOD_S = 1.7
SPIKE_HEAD_CONTACT_DAMAGE = 16.0
SPIKE_HEAD_AMPLITUDE_TILES = 0.8
SPIKE_HEAD_PERIOD_S = 1.4
SPIKED_BALL_CONTACT_DAMAGE = 22.0
SPIKED_BALL_AMPLITUDE_TILES = 1.6
SPIKED_BALL_PERIOD_S = 2.4

# --- Static cave-floor hazards (Spikes, Fire, Arrow Trap, Falling Platform) ---
# One shared per-column roll (mutually exclusive, like the crate/bush roll
# in world_generator._place_forest_decoration) picks at most one of these
# for a valid cave-floor spot -- environmental hazards the player finds
# while exploring, not something they craft/place themselves.
CAVE_HAZARD_SPAWN_CHANCE_PER_COLUMN = 0.018
FIRE_CONTACT_DAMAGE = 14.0
ARROW_TRAP_CONTACT_DAMAGE = 10.0

# --- Fan shafts (a rarer roll needing a small vertical air pocket) ---
FAN_SHAFT_SPAWN_CHANCE_PER_COLUMN = 0.006

# --- Biome-flavored surface traps (Sand/Desert, Ice/Snow, Mud/Jungle) ---
SURFACE_TRAP_SPAWN_CHANCE_PER_COLUMN = 0.02

# --- Checkpoints ---
# Activation is exact-tile-overlap (like Spikes/Trampoline), no separate
# radius check needed.

# --- Building: Doors & Beds (user-requested construction system) ---
# A Door toggles between a solid (closed) and passable (open) tile on T,
# same "swap the actual stored tile id" trick Falling Platform already
# uses for its crumble/respawn state (see World.set_tile). A Bed lets the
# player skip to morning (WorldClock.skip_to_morning) at night, but only
# if it's inside a real, bounded, walled-and-roofed space -- see
# game/world/shelter.py's flood fill. Both are found via the same
# STATION_SEARCH_RADIUS_TILES proximity check T already uses for NPCs/chests.
# The flood fill from the bed's own tile stops counting a space as
# "enclosed" once it has visited more open tiles than this -- either it
# leaked out into the open world, or it's just too big to read as a cozy,
# safe room. ~14x14 tiles of open interior at the default value.
SHELTER_MAX_AIR_TILES = 200
# A brief black-screen fade-out right after a successful sleep -- an
# instant clock jump otherwise reads as a glitch, not a night passing.
SLEEP_FADE_DURATION_S = 0.6

# --- Particles ---
PARTICLE_DUST_LIFETIME_S = 0.4
PARTICLE_DUST_STEP_INTERVAL_S = 0.28  # min gap between footstep puffs while running on ground
PARTICLE_CONFETTI_LIFETIME_S = 1.1
PARTICLE_CONFETTI_COUNT = 26
PARTICLE_HIT_SPARK_LIFETIME_S = 0.22
PARTICLE_HIT_SPARK_COUNT = 6

# --- Furnace / smelting ---
SMELT_TIME_IRON_S = 4.0
SMELT_TIME_STEEL_S = 8.0  # iron bar re-smelted -- slower, next mining tier
SMELT_TIME_GEM_S = 6.0  # topaz/sapphire/emerald -- rarer ore, slower burn

# --- Magic-tier gear (crafted from an Arcane Bar = all three gem bars) ---
ARCANE_PICKAXE_FORTUNE_CHANCE = 0.25
ARCANE_HELM_LIGHT_EMIT = 12  # a bit under a torch (14), enough to mine without placing lights

# --- On-screen notifications (recipe unlocks, blocked-mining messages) ---
NOTIFICATION_DURATION_S = 2.5

# --- Procedural structures (Phase 7) ---
# A coarse slot grid, the same deterministic-per-slot pattern trees use
# (see world_generator.TREE_SLOT_WIDTH) but much wider, since structures
# are rarer and bigger. See game/world/structures.py.
STRUCTURE_SLOT_WIDTH_TILES = 40
STRUCTURE_SPAWN_CHANCE_PER_SLOT = 0.35
STRUCTURE_MARGIN_TILES = 6  # keeps an anchor away from its slot's edges so neighboring slots' footprints can never overlap
STRUCTURE_MAX_TERRAIN_VARIANCE_TILES = 3  # skip a surface structure if the ground varies more than this across its footprint
UNDERGROUND_ROOM_MIN_DEPTH_BELOW_SURFACE = 14
RUINS_WALL_COLLAPSE_CHANCE = 0.35  # each Ruins wall tile independently has this chance to be missing

# --- NPCs (Phase 8) ---
# Interact radius is in tiles from player center to NPC center. Homes
# prefer a world-generated House (see game/world/structures.py); Guide
# stays near spawn so the first NPC is actually findable, Merchant/
# Blacksmith can live farther out as an exploration reward.
NPC_INTERACT_RANGE_TILES = 3.0
NPC_GUIDE_MAX_HOUSE_DISTANCE_TILES = 80
NPC_HOME_SEARCH_MAX_DISTANCE_TILES = 400
# Merchant arrives once inventory wealth (sum of item.value * qty, not
# counting equipped gear) reaches this -- the starting wood pickaxe is
# worth 10, so this is "you've gathered a bit of loot", not "you spawned".
NPC_MERCHANT_MIN_WEALTH = 25
NPC_WIDTH_TILES = 0.8
NPC_HEIGHT_TILES = 1.8

# --- Save / load ---
SAVE_FILE_PATH = os.path.join("saves", "save.json")
NOTIFICATION_THROTTLE_S = 1.5  # min gap between repeats of the *same* blocked-action message

# --- Floating damage numbers ---
DAMAGE_POPUP_LIFETIME_S = 0.8
DAMAGE_POPUP_RISE_PX_PER_S = 52.0

# --- Enemy-fired projectiles (boss ranged attacks) ---
ENEMY_PROJECTILE_SIZE_TILES = 0.35
ENEMY_PROJECTILE_LIFETIME_S = 3.0
ENEMY_PROJECTILE_GRAVITY_SCALE = 0.35  # fraction of world GRAVITY, same idea as PROJECTILE_GRAVITY_SCALE

# --- Boss: Slime King (Phase 10) ---
# Phases are keyed off remaining-health ratio (1.0 -> 0.0), not a separate
# timer -- entering a lower phase is permanent since health only ever goes
# down, exactly the "no going back" progression a real boss fight needs.
# See game/entities/boss_ai.py.
#
# Retuned (user feedback: "ele nem tá me acertando no pulo, crie
# projéteis, deixe ele mais forte"): the hop used to aim at wherever the
# player happened to be standing *when the hop launched*, then commit to
# that fixed horizontal velocity for the whole arc -- an easy dodge, since
# SLIME_KING_MOVE_SPEED (4.5) was even slower than the player's own move
# speed (5.5). It now leads the player's current velocity to predict
# where they'll actually be when it lands (see boss_ai._update_hop_movement),
# is faster than the player outright, and hops more often. The ranged
# attack fans out into SLIME_KING_SPREAD_COUNT projectiles once enraged,
# instead of one lob at a time. Damage/health are up across the board.
BOSS_PHASE_2_HEALTH_RATIO = 0.66  # <= this ratio: adds the ranged Slime Lob attack
BOSS_PHASE_3_HEALTH_RATIO = 0.33  # <= this ratio: enrages -- summons minions once, hops/attacks faster, gains a landing shockwave
SLIME_KING_MAX_HEALTH = 620.0
SLIME_KING_CONTACT_DAMAGE = 30.0
SLIME_KING_MOVE_SPEED = 6.5  # faster than PLAYER_MOVE_SPEED (5.5) -- it used to be slower, an easy walk-away
SLIME_KING_WIDTH_TILES = 2.4
SLIME_KING_HEIGHT_TILES = 1.8
SLIME_KING_HOP_IMPULSE = 13.0
SLIME_KING_HOP_INTERVAL_MIN_S = 0.35
SLIME_KING_HOP_INTERVAL_MAX_S = 0.8
SLIME_KING_PHASE_SPEED_MULT = (1.0, 1.3, 1.75)  # hop speed/frequency scale, indexed by phase_index (0/1/2)
# The hop's horizontal speed is solved to land on the player's *predicted*
# position (their current position + velocity * time-of-flight), capped
# at move_speed * phase_mult * this -- otherwise a target far away would
# demand an absurdly fast lunge to land exactly on them in one arc.
SLIME_KING_HOP_LEAD_SPEED_MULT = 1.4
SLIME_KING_LOB_DAMAGE = 18.0
SLIME_KING_LOB_SPEED = 10.0
SLIME_KING_LOB_COOLDOWN_S = 1.8  # divided by SLIME_KING_PHASE_SPEED_MULT[phase_index]
SLIME_KING_SPREAD_COUNT = 3  # projectiles fired at once, phase 3 (enraged) only -- 1 in phase 2
SLIME_KING_SPREAD_ANGLE_DEGREES = 16.0  # angular gap between each shot in the phase-3 fan
SLIME_KING_MINION_COUNT = 2  # regular Slimes summoned once, on entering phase 3
SLIME_KING_STOMP_DAMAGE = 22.0
SLIME_KING_STOMP_RADIUS_TILES = 3.0  # phase-3 landing shockwave -- hits even without a direct hitbox overlap
BOSS_COIN_BOUNTY = 90  # bonus coins granted on top of the guaranteed exclusive drop

# --- Debug tools (F4 toggles debug_mode; F5-F11 while it's on -- see
# GameApp's debug_* methods, InputHandler._handle_keydown, and README
# "How the debug tools work"). Developer-only, gated behind the toggle so
# a stray keypress during normal play can never trigger one. ---
DEBUG_RESTOCK_COINS = 999
DEBUG_SPAWN_SPACING_TILES = 2  # horizontal gap between each debug-spawned entity, so they don't stack
