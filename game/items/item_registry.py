"""Central, data-driven table of every item in the game (see tile_registry.py
for the equivalent tile table). Adding an item means adding one entry here.

Categories present (see README "Como adicionar um novo item"):
- BLOCK / ORE / TOOL / DECORATION / MATERIAL / WEAPON / ARMOR: fully
  functional -- obtainable by mining/chopping/crafting/enemy drops and
  usable (equipped, in the case of armor -- see game/inventory/equipment.py)
  through Phase 3 crafting, Phase 4 combat and the equipment pass. This
  includes each biome's ground blocks (sand/sandstone, snow/frozen dirt,
  jungle grass/mud), each biome's deep-underground stone (desert/snow/jungle
  stone), the desert-exclusive `cactus_fiber` material, and the three
  biome-exclusive gems (topaz/sapphire/emerald). Each gem smelts into a
  bar; the three bars combine into an Arcane Bar that crafts magic-tier
  gear (pickaxe with fortune, a no-ammo Magic staff, a helm that emits light).
- CONSUMABLE: `arrow` is fully functional (bow ammo). Food items (apple and
  the six other fruits) are fully functional too: obtainable from a rare
  "Berry Bush" surface spawn (`BUSH_ID`'s `drop_pool`) and eaten with the F
  key (`Player.eat_selected`), which heals `heal_amount` HP and consumes one.
  `slime_core_idol` is also fully functional: used with G
  (`Player.use_selected_summon_item`) to spawn the Slime King boss (Phase
  10) -- its exclusive drop `slime_king_core` crafts into the best head
  armor in the game, `slime_king_crown`.
"""
from typing import Dict

from game.items.item import ItemDef, ItemCategory, ItemRarity
from game.world import tile_registry
from game.settings import DEFAULT_STACK_SIZE, ARCANE_PICKAXE_FORTUNE_CHANCE, ARCANE_HELM_LIGHT_EMIT

_ITEMS: Dict[str, ItemDef] = {}


def _register(item: ItemDef) -> None:
    if item.id in _ITEMS:
        raise ValueError(f"Duplicate item id {item.id}")
    _ITEMS[item.id] = item


# --- Blocks (placeable, obtained by mining) ---

_register(ItemDef(
    id="dirt_block", name="Dirt Block",
    description="Common soil. Placeable and easy to dig through.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1,
    places_tile_id=tile_registry.DIRT_ID,
))

_register(ItemDef(
    id="stone_block", name="Stone Block",
    description="Solid rock. Requires a pickaxe to mine, but can be placed by hand.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.STONE_ID,
))

_register(ItemDef(
    id="wood_plank_block", name="Wood Plank",
    description="Cut planks. Placeable building block crafted from wood.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.WOOD_PLANK_ID,
))

# --- Biome ground blocks (placeable, obtained by mining -- see biome_registry.py) ---

_register(ItemDef(
    id="sand_block", name="Sand Block",
    description="Loose desert sand. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1,
    places_tile_id=tile_registry.SAND_ID,
))

_register(ItemDef(
    id="sandstone_block", name="Sandstone Block",
    description="Sand fused solid by desert heat. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.SANDSTONE_ID,
))

_register(ItemDef(
    id="snow_block", name="Snow Block",
    description="Packed snow. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1,
    places_tile_id=tile_registry.SNOW_BLOCK_ID,
))

_register(ItemDef(
    id="frozen_dirt_block", name="Frozen Dirt Block",
    description="Soil hardened by cold. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.FROZEN_DIRT_ID,
))

_register(ItemDef(
    id="jungle_grass_block", name="Jungle Grass Block",
    description="Dense, humid topsoil. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1,
    places_tile_id=tile_registry.JUNGLE_GRASS_ID,
))

_register(ItemDef(
    id="mud_block", name="Mud Block",
    description="Waterlogged jungle soil. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.MUD_ID,
))

# --- Biome-specific underground stone (placeable, obtained by mining --
# see biome_registry.py underground_tile_id) ---

_register(ItemDef(
    id="desert_stone_block", name="Desert Stone Block",
    description="Sun-baked rock from beneath the desert. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.DESERT_STONE_ID,
))

_register(ItemDef(
    id="snow_stone_block", name="Permafrost Stone Block",
    description="Frost-cracked rock from beneath the snow. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.SNOW_STONE_ID,
))

_register(ItemDef(
    id="jungle_stone_block", name="Jungle Stone Block",
    description="Moss-covered rock from beneath the jungle. Placeable.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2,
    places_tile_id=tile_registry.JUNGLE_STONE_ID,
))

# --- Ores (raw resources, obtained by mining; icon is a loose-ore-chunk
# icon from the user-supplied icon sheet -- see assets._SHEET_ICON_CELLS --
# rather than a reused tile texture, which read more like carrying a block
# than a handful of ore) ---

_register(ItemDef(
    id="coal", name="Coal",
    description="A dark, combustible mineral found in shallow deposits.",
    category=ItemCategory.ORE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=3,
    icon_key="coal",
))

_register(ItemDef(
    id="iron_ore", name="Iron Ore",
    description="Raw iron. Smelt it at a Furnace (with Coal as fuel) into an Iron Bar.",
    category=ItemCategory.ORE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=6,
    icon_key="iron_ore",
))

# --- Biome-exclusive gems (rare deep-underground finds, one per non-forest
# biome -- see biome_registry.py exclusive_ore_tile_id). Each smelts into
# its own bar at a Furnace, same as iron_ore -- see smelt_registry.py. ---

_register(ItemDef(
    id="topaz", name="Topaz",
    description="A golden gem found deep beneath the desert. Smeltable into a Topaz Bar, which feeds an Arcane Bar.",
    category=ItemCategory.ORE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=15,
    icon_key="topaz",
))

_register(ItemDef(
    id="sapphire", name="Sapphire",
    description="A blue gem found deep beneath the snow. Smeltable into a Sapphire Bar, which feeds an Arcane Bar.",
    category=ItemCategory.ORE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=15,
    icon_key="sapphire",
))

_register(ItemDef(
    id="emerald", name="Emerald",
    description="A green gem found deep beneath the jungle. Smeltable into an Emerald Bar, which feeds an Arcane Bar.",
    category=ItemCategory.ORE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=15,
    icon_key="emerald",
))

# --- Bars (smelted at a Furnace from the ores above -- see
# game/crafting/smelt_registry.py and furnace_system.py). No dedicated art
# exists for any of these, so they get a hand-drawn vector icon like the
# tools/weapons below (see assets.py's _build_procedural_icons). ---

_register(ItemDef(
    id="iron_bar", name="Iron Bar",
    description="Smelted from Iron Ore and Coal. Used to craft an Iron Pickaxe and Iron armor, or re-smelted into Steel.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=14,
    icon_key="iron_bar",
))

_register(ItemDef(
    id="steel_bar", name="Steel Bar",
    description="Re-smelted from Iron Bars and extra Coal. Used to craft a Steel Pickaxe and Steel armor.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=28,
    icon_key="steel_bar",
))

_register(ItemDef(
    id="topaz_bar", name="Topaz Bar",
    description="Smelted from Topaz and Coal. Combined with Sapphire and Emerald Bars into an Arcane Bar.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=32,
    icon_key="topaz_bar",
))

_register(ItemDef(
    id="sapphire_bar", name="Sapphire Bar",
    description="Smelted from Sapphire and Coal. Combined with Topaz and Emerald Bars into an Arcane Bar.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=32,
    icon_key="sapphire_bar",
))

_register(ItemDef(
    id="emerald_bar", name="Emerald Bar",
    description="Smelted from Emerald and Coal. Combined with Topaz and Sapphire Bars into an Arcane Bar.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=32,
    icon_key="emerald_bar",
))

_register(ItemDef(
    id="arcane_bar", name="Arcane Bar",
    description="Forged from one Topaz, Sapphire and Emerald Bar. The magic-tier material: pickaxe, staff and helm.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.EPIC, value=90,
    icon_key="arcane_bar",
))

# --- Tools ---

_register(ItemDef(
    id="wood_pickaxe", name="Wood Pickaxe",
    description="A basic pickaxe. Can break stone and ore.",
    category=ItemCategory.TOOL, max_stack=1,
    rarity=ItemRarity.COMMON, value=10, max_durability=60,
    is_tool=True, mining_power=1.5, tool_type="pickaxe",
    icon_key="wood_pickaxe",
))

_register(ItemDef(
    id="stone_pickaxe", name="Stone Pickaxe",
    description="A sturdier pickaxe crafted at a workbench. Mines faster than the wood pickaxe.",
    category=ItemCategory.TOOL, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=25, max_durability=150,
    is_tool=True, mining_power=3.0, tool_type="pickaxe",
    icon_key="stone_pickaxe",
))

_register(ItemDef(
    id="iron_pickaxe", name="Iron Pickaxe",
    description="Forged from a smelted Iron Bar. Mines faster than the stone pickaxe.",
    category=ItemCategory.TOOL, max_stack=1,
    rarity=ItemRarity.RARE, value=45, max_durability=300,
    is_tool=True, mining_power=5.0, tool_type="pickaxe",
    icon_key="iron_pickaxe",
))

_register(ItemDef(
    id="steel_pickaxe", name="Steel Pickaxe",
    description="Forged from Steel Bars. Mines faster than the iron pickaxe.",
    category=ItemCategory.TOOL, max_stack=1,
    rarity=ItemRarity.RARE, value=70, max_durability=450,
    is_tool=True, mining_power=7.0, tool_type="pickaxe",
    icon_key="steel_pickaxe",
))

_register(ItemDef(
    id="arcane_pickaxe", name="Arcane Pickaxe",
    description="Forged from an Arcane Bar. Mines faster than steel and has a chance to yield an extra drop.",
    category=ItemCategory.TOOL, max_stack=1,
    rarity=ItemRarity.EPIC, value=95, max_durability=600,
    is_tool=True, mining_power=9.0, tool_type="pickaxe",
    fortune_chance=ARCANE_PICKAXE_FORTUNE_CHANCE,
    icon_key="arcane_pickaxe",
))

# --- Decoration (placeable, obtained by mining a rare surface spawn) ---

_register(ItemDef(
    id="wooden_crate", name="Wooden Crate",
    description="A sturdy crate. Purely decorative for now.",
    category=ItemCategory.DECORATION, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=8,
    places_tile_id=tile_registry.DECOR_CRATE_ID,
))

_register(ItemDef(
    id="workbench", name="Workbench",
    description="A crafting station. Stand near it to craft recipes that require one.",
    category=ItemCategory.DECORATION, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=5,
    places_tile_id=tile_registry.WORKBENCH_ID,
))

_register(ItemDef(
    id="furnace", name="Furnace",
    description="Stand near it to smelt ore (plus Coal as fuel) into bars over time.",
    category=ItemCategory.DECORATION, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=12,
    places_tile_id=tile_registry.FURNACE_ID,
))

_register(ItemDef(
    id="personal_chest", name="Personal Chest",
    description="Place it and press T nearby to open your personal stash. Every chest shares the same storage.",
    category=ItemCategory.DECORATION, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=10,
    places_tile_id=tile_registry.PERSONAL_CHEST_ID,
))

_register(ItemDef(
    id="torch", name="Torch",
    description="Lights up nearby tiles. Place it to push back the dark.",
    category=ItemCategory.DECORATION, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=3,
    places_tile_id=tile_registry.TORCH_ID,
))

# --- Currency (Phase 8 shops). Obtained by selling items to the Merchant
# or Blacksmith; spent on their shop stock. Not crafted, not mined.
# max_stack is huge so a full-stack sale (bag stuffed, no existing coin
# pile) always fits in the one slot the sold stack just freed. ---

_register(ItemDef(
    id="coin", name="Coin",
    description="Currency. Sell items to a Merchant or Blacksmith to earn coins, then spend them in their shop.",
    category=ItemCategory.MATERIAL, max_stack=9999,
    rarity=ItemRarity.COMMON, value=1, icon_key="coin",
))

# --- Material (obtained by chopping trees) ---

_register(ItemDef(
    id="wood", name="Wood",
    description="Sturdy timber, chopped from trees.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1,
    icon_tile_id=tile_registry.TREE_TRUNK_ID,
))

_register(ItemDef(
    id="cactus_fiber", name="Cactus Fiber",
    description="Tough fiber stripped from a desert cactus.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1,
    icon_tile_id=tile_registry.CACTUS_ID,
))

_register(ItemDef(
    id="slime_gel", name="Slime Gel",
    description="A blob of gel left behind by a slime.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="slime_gel",
))

_register(ItemDef(
    id="feather", name="Feather",
    description="A light feather, shed by a flying creature.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="feather",
))

# --- Weapon (crafted at a workbench; see recipe_registry.py) ---

_register(ItemDef(
    id="wood_sword", name="Wood Sword",
    description="A simple melee weapon. Left-click near an enemy to swing it.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.COMMON, value=12, damage=8.0, speed=3.0,
    max_durability=80, icon_key="wood_sword",
    is_weapon=True, is_ranged=False,
))

_register(ItemDef(
    id="iron_sword", name="Iron Sword",
    description="Forged from a smelted Iron Bar. Hits harder than the wood sword.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=34, damage=14.0, speed=2.8,
    max_durability=400, icon_key="iron_sword",
    is_weapon=True, is_ranged=False,
))

_register(ItemDef(
    id="steel_sword", name="Steel Sword",
    description="Forged from Steel Bars. Hits harder than the iron sword.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.RARE, value=58, damage=20.0, speed=2.6,
    max_durability=600, icon_key="steel_sword",
    is_weapon=True, is_ranged=False,
))

_register(ItemDef(
    id="wood_bow", name="Wood Bow",
    description="A simple bow. Fires an arrow per shot; needs arrows in the inventory.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=20, damage=6.0, speed=1.5,
    max_durability=60, icon_key="wood_bow",
    is_weapon=True, is_ranged=True, ammo_item_id="arrow",
))

_register(ItemDef(
    id="iron_bow", name="Iron Bow",
    description="A reinforced bow with an iron-strung frame. Fires an arrow per shot; needs arrows in the inventory.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.RARE, value=42, damage=11.0, speed=1.4,
    max_durability=300, icon_key="iron_bow",
    is_weapon=True, is_ranged=True, ammo_item_id="arrow",
))

_register(ItemDef(
    id="steel_bow", name="Steel Bow",
    description="A hardened steel bow with a stiffer draw. Fires an arrow per shot; needs arrows in the inventory.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.RARE, value=65, damage=16.0, speed=1.3,
    max_durability=450, icon_key="steel_bow",
    is_weapon=True, is_ranged=True, ammo_item_id="arrow",
))

_register(ItemDef(
    id="arrow", name="Arrow",
    description="Ammunition for a bow. Consumed on each shot.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=1, icon_key="arrow",
))

_register(ItemDef(
    id="arcane_staff", name="Arcane Staff",
    description="Fires a magic bolt that uses no ammo. Damage and XP go through Magic, not Attack. Straight flight, no gravity arc.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.EPIC, value=88, damage=10.0, speed=2.0,
    max_durability=200, icon_key="arcane_staff",
    is_weapon=True, is_ranged=True, uses_magic=True,
    crit_chance=0.1, crit_damage_mult=1.4,
))

_register(ItemDef(
    id="arcane_sword", name="Arcane Sword",
    description="Forged from an Arcane Bar and etched with a crackling edge. Hits harder than steel and can land a critical strike.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.EPIC, value=100, damage=28.0, speed=3.0,
    max_durability=520, icon_key="arcane_sword",
    is_weapon=True, is_ranged=False,
    crit_chance=0.15, crit_damage_mult=1.6,
))

# --- Summon rods (Summoner-class-only weapons; see class_registry.py and
# game/entities/summon_registry.py). Casting one replaces the player's
# current summon -- only one can be active at a time. ---

_register(ItemDef(
    id="summon_rod_wood", name="Twig Rod",
    description="A crude rod bound with a scrap of slime gel. Summons a Twig Sprite to fight for you.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.COMMON, value=15, speed=1.0,
    icon_key="summon_rod_wood",
    is_weapon=True, is_ranged=False, weapon_class="summon", summons_id="twig_sprite",
))

_register(ItemDef(
    id="summon_rod_iron", name="Iron Rod",
    description="A rod forged from a smelted Iron Bar. Summons a much sturdier Iron Guardian.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.RARE, value=40, speed=1.2,
    icon_key="summon_rod_iron",
    is_weapon=True, is_ranged=False, weapon_class="summon", summons_id="iron_guardian",
))

_register(ItemDef(
    id="summon_rod_steel", name="Steel Rod",
    description="A rod forged from hardened Steel Bars. Summons a Steel Colossus, sturdier still than the Iron Guardian.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.RARE, value=65, speed=1.3,
    icon_key="summon_rod_steel",
    is_weapon=True, is_ranged=False, weapon_class="summon", summons_id="steel_colossus",
))

_register(ItemDef(
    id="summon_rod_arcane", name="Arcane Rod",
    description="A rod bound from an Arcane Bar. Summons an Arcane Familiar, the strongest minion available.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.EPIC, value=110, speed=1.3,
    icon_key="summon_rod_arcane",
    is_weapon=True, is_ranged=False, weapon_class="summon", summons_id="arcane_familiar",
))

# --- Armor (equip via the inventory screen; see game/inventory/equipment.py) ---

_register(ItemDef(
    id="wood_helmet", name="Wood Helmet",
    description="Basic head armor carved from wood. Reduces incoming damage.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.COMMON, value=15, max_durability=100,
    icon_key="wood_helmet", equip_slot="head", defense=4.0,
))

_register(ItemDef(
    id="wood_armor", name="Wood Armor",
    description="A sturdy wooden chestpiece crafted at a workbench. Reduces incoming damage.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=28, max_durability=140,
    icon_key="wood_armor", equip_slot="body", defense=6.0,
))

_register(ItemDef(
    id="wood_greaves", name="Wood Greaves",
    description="Wooden leg armor. Reduces incoming damage.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.COMMON, value=18, max_durability=100,
    icon_key="wood_greaves", equip_slot="legs", defense=3.0,
))

_register(ItemDef(
    id="wood_boots", name="Wood Boots",
    description="Wooden boots. Reduces incoming damage.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.COMMON, value=12, max_durability=80,
    icon_key="wood_boots", equip_slot="boots", defense=2.0,
))

_register(ItemDef(
    id="iron_helmet", name="Iron Helmet",
    description="Forged head armor. Stronger than wood.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=32, max_durability=180,
    icon_key="iron_helmet", equip_slot="head", defense=7.0,
))

_register(ItemDef(
    id="iron_armor", name="Iron Armor",
    description="A forged iron chestpiece. Stronger than wood.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.RARE, value=50, max_durability=240,
    icon_key="iron_armor", equip_slot="body", defense=10.0,
))

_register(ItemDef(
    id="iron_greaves", name="Iron Greaves",
    description="Forged leg armor. Stronger than wood.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=38, max_durability=180,
    icon_key="iron_greaves", equip_slot="legs", defense=6.0,
))

_register(ItemDef(
    id="iron_boots", name="Iron Boots",
    description="Forged iron boots. Stronger than wood.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=24, max_durability=140,
    icon_key="iron_boots", equip_slot="boots", defense=4.0,
))

_register(ItemDef(
    id="steel_helmet", name="Steel Helmet",
    description="Hardened steel head armor. Stronger than iron.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.RARE, value=50, max_durability=260,
    icon_key="steel_helmet", equip_slot="head", defense=10.0,
))

_register(ItemDef(
    id="steel_armor", name="Steel Armor",
    description="A hardened steel chestpiece. Stronger than iron.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.RARE, value=80, max_durability=340,
    icon_key="steel_armor", equip_slot="body", defense=14.0,
))

_register(ItemDef(
    id="steel_greaves", name="Steel Greaves",
    description="Hardened steel leg armor. Stronger than iron.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.RARE, value=62, max_durability=260,
    icon_key="steel_greaves", equip_slot="legs", defense=9.0,
))

_register(ItemDef(
    id="steel_boots", name="Steel Boots",
    description="Hardened steel boots. Stronger than iron.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.RARE, value=40, max_durability=200,
    icon_key="steel_boots", equip_slot="boots", defense=6.0,
))

_register(ItemDef(
    id="arcane_helmet", name="Arcane Helm",
    description="Forged from an Arcane Bar. Stronger than steel, and it glows so you can mine without placing torches.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=85, max_durability=320,
    icon_key="arcane_helmet", equip_slot="head", defense=12.0,
    light_emit=ARCANE_HELM_LIGHT_EMIT,
))

_register(ItemDef(
    id="arcane_body", name="Arcane Robe",
    description="Forged from an Arcane Bar. Stronger than steel.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=130, max_durability=420,
    icon_key="arcane_body", equip_slot="body", defense=16.0,
))

_register(ItemDef(
    id="arcane_greaves", name="Arcane Greaves",
    description="Forged from an Arcane Bar. Stronger than steel.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=95, max_durability=320,
    icon_key="arcane_greaves", equip_slot="legs", defense=11.0,
))

_register(ItemDef(
    id="arcane_boots", name="Arcane Boots",
    description="Forged from an Arcane Bar. Stronger than steel.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=62, max_durability=250,
    icon_key="arcane_boots", equip_slot="boots", defense=7.0,
))

# --- Accessory (equip via the inventory screen; unlike armor, actively
# used with E -- see Player.try_use_accessory, game/entities/grapple.py) ---


# --- Post-Arcane tier: Voidstone / Voidsteel (a brand-new material tier one
# step above Arcane in every stat -- Voidstone is a universal, very-deep-
# only ore, see tile_registry.VOID_ORE_ID and world_generator._void_ore_roll.
# It smelts into a Voidsteel Bar (see smelt_registry.py) which forges the
# strongest sword, full armor set, accessory and Summoner rod in the game.
# All EPIC rarity, all crafted at the existing Workbench. ---

_register(ItemDef(
    id="voidstone", name="Voidstone",
    description="A pitch-black ore laced with faint violet veins, found only in the deepest, most dangerous caverns -- far below where Iron or any gem turns up. Smelt it at a Furnace (with Coal as fuel) into a Voidsteel Bar.",
    category=ItemCategory.ORE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.EPIC, value=200, icon_key="voidstone",
))

_register(ItemDef(
    id="voidsteel_bar", name="Voidsteel Bar",
    description="Smelted from Voidstone and Coal -- the slowest, toughest smelt there is. Forges the strongest gear in the game.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.EPIC, value=260, icon_key="voidsteel_bar",
))

_register(ItemDef(
    id="voidsteel_sword", name="Voidsteel Sword",
    description="A blade forged from Voidsteel. Left-click near an enemy to swing it -- the hardest-hitting melee weapon in the game.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.EPIC, value=220, damage=38.0, speed=3.5,
    max_durability=700, icon_key="voidsteel_sword",
    is_weapon=True, is_ranged=False,
))

_register(ItemDef(
    id="voidsteel_helmet", name="Voidsteel Helm",
    description="Head armor forged from Voidsteel. The strongest helmet in the game.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=200, max_durability=500,
    icon_key="voidsteel_helmet", equip_slot="head", defense=19.0,
))

_register(ItemDef(
    id="voidsteel_armor", name="Voidsteel Armor",
    description="A Voidsteel chestpiece. The strongest body armor in the game.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=260, max_durability=560,
    icon_key="voidsteel_armor", equip_slot="body", defense=21.0,
))

_register(ItemDef(
    id="voidsteel_greaves", name="Voidsteel Greaves",
    description="Voidsteel leg armor. The strongest leg armor in the game.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=210, max_durability=500,
    icon_key="voidsteel_greaves", equip_slot="legs", defense=14.5,
))

_register(ItemDef(
    id="voidsteel_boots", name="Voidsteel Boots",
    description="Voidsteel boots. The strongest boots in the game.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=160, max_durability=440,
    icon_key="voidsteel_boots", equip_slot="boots", defense=10.5,
))

_register(ItemDef(
    id="voidstone_amulet", name="Voidstone Amulet",
    description="Equip in the accessory slot. A raw, uncut shard of Voidstone that radiates protection and an eerie violet light.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.EPIC, value=180, max_durability=None,
    icon_key="voidstone_amulet", equip_slot="accessory", defense=8.0, light_emit=13,
))

_register(ItemDef(
    id="summon_rod_voidsteel", name="Voidsteel Rod",
    description="A rod forged from Voidsteel, humming with contained power. Summons a Void Wraith -- the most powerful minion a Summoner can call.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.EPIC, value=220, speed=1.4,
    icon_key="summon_rod_voidsteel",
    is_weapon=True, is_ranged=False, weapon_class="summon", summons_id="void_wraith",
))

_register(ItemDef(
    id="grapple_hook", name="Grapple Hook",
    description="Equip in the accessory slot. Press E to fire it -- if it catches a wall, you're pulled to it and held there, making climbing much easier. Press E again (or jump) to let go.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=30, max_durability=None,
    icon_key="grapple_hook", equip_slot="accessory", accessory_kind="grapple_hook",
))

_register(ItemDef(
    id="warriors_charm", name="Warrior's Charm",
    description="Equip in the accessory slot. A sturdy charm worn by front-line fighters -- passively reduces incoming damage.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.RARE, value=45, max_durability=None,
    icon_key="warriors_charm", equip_slot="accessory", defense=6.0,
))

_register(ItemDef(
    id="summoners_trinket", name="Summoner's Trinket",
    description="Equip in the accessory slot. A faintly glowing trinket favored by summoners -- passively reduces incoming damage and lights up nearby tiles.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.RARE, value=45, max_durability=None,
    icon_key="summoners_trinket", equip_slot="accessory", defense=3.0, light_emit=6,
))

_register(ItemDef(
    id="swift_anklet", name="Swift Anklet",
    description="Equip in the accessory slot for a passive boost to move speed.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.RARE, value=45, max_durability=None,
    icon_key="swift_anklet", equip_slot="accessory", move_speed_bonus=1.0,
))

_register(ItemDef(
    id="arcane_anklet", name="Arcane Anklet",
    description="Equip in the accessory slot for a stronger passive boost to move speed, woven from an Arcane Bar.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.EPIC, value=95, max_durability=None,
    icon_key="arcane_anklet", equip_slot="accessory", move_speed_bonus=1.5,
))

# --- Consumable: food (fully functional -- eat with F to heal; obtained
# from a rare Berry Bush surface spawn, see BUSH_ID) ---

_register(ItemDef(
    id="apple", name="Apple",
    description="A fresh apple. Press F to eat and restore 20 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="apple", heal_amount=20.0,
))

_register(ItemDef(
    id="banana", name="Banana",
    description="Press F to eat and restore 12 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="banana", heal_amount=12.0,
))

_register(ItemDef(
    id="cherries", name="Cherries",
    description="Press F to eat and restore 10 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="cherries", heal_amount=10.0,
))

_register(ItemDef(
    id="kiwi", name="Kiwi",
    description="Press F to eat and restore 14 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="kiwi", heal_amount=14.0,
))

_register(ItemDef(
    id="melon", name="Melon",
    description="Press F to eat and restore 25 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=3, icon_key="melon", heal_amount=25.0,
))

_register(ItemDef(
    id="orange", name="Orange",
    description="Press F to eat and restore 15 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="orange", heal_amount=15.0,
))

_register(ItemDef(
    id="pineapple", name="Pineapple",
    description="Press F to eat and restore 22 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=3, icon_key="pineapple", heal_amount=22.0,
))

_register(ItemDef(
    id="strawberry", name="Strawberry",
    description="Press F to eat and restore 10 HP.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=2, icon_key="strawberry", heal_amount=10.0,
))

# --- Trampoline: the one "trap"-sheet item that's a bounce pad, not a
# hazard, so it stays player-craftable/placeable (see TileDef.bounce_velocity).
# Spikes, Fan, Sand/Mud/Ice traps and Falling Platform are environmental
# hazards generated by world_generator.py -- the player finds them, they
# don't craft or place them, so there's no item for any of those (see
# tile_registry.py). ---

_register(ItemDef(
    id="trampoline", name="Trampoline",
    description="Launches you into the air when you land on it.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=10,
    places_tile_id=tile_registry.TRAMPOLINE_ID,
))

_register(ItemDef(
    id="checkpoint", name="Checkpoint",
    description="Place it and touch it once to make it your new respawn point.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.RARE, value=20,
    places_tile_id=tile_registry.CHECKPOINT_ID,
))

# --- Building: Doors & Beds (user-requested construction system) ---

_register(ItemDef(
    id="door", name="Wood Door",
    description="Press T to open or close. Build walls from Wood Plank/Stone Blocks around one so you're not sealed in your own house.",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=6,
    places_tile_id=tile_registry.DOOR_CLOSED_ID,
))

_register(ItemDef(
    id="bed", name="Bed",
    description="Press T to sleep and skip to morning. Only works at night, inside a real enclosed room (walls, floor and a roof).",
    category=ItemCategory.BLOCK, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=14,
    places_tile_id=tile_registry.BED_ID,
))


# --- Boss: Slime King (Phase 10) ---

_register(ItemDef(
    id="slime_core_idol", name="Slime Core Idol",
    description="A pulsing idol bound from concentrated slime gel. Press G to summon the Slime King nearby.",
    category=ItemCategory.CONSUMABLE, max_stack=10,
    rarity=ItemRarity.RARE, value=0,
    summons_boss_id="slime_king",
    icon_key="slime_core_idol",
))

_register(ItemDef(
    id="slime_king_core", name="Slime King's Core",
    description="The crystallized heart of the Slime King. Drops only from defeating it.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.EPIC, value=120,
    icon_key="slime_king_core",
))

_register(ItemDef(
    id="slime_king_crown", name="Crown of the Slime King",
    description="Forged from the Slime King's Core and Steel. A trophy that's also the best head armor in the game.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=140, max_durability=400,
    equip_slot="head", defense=16.0,
    icon_key="slime_king_crown",
))

# Two more Slime-King-themed recipes off the same exclusive drop (see
# recipe_registry.py) -- a farmable alternative/side-grade to the Voidsteel
# tier above, not strictly required progression. Each still costs its own
# 1x slime_king_core, so a full themed set means multiple boss kills, same
# as the existing Crown.

_register(ItemDef(
    id="slime_king_fang", name="Fang of the Slime King",
    description="A blade carved from the Slime King's crystallized Core and hardened Steel. A farmable weapon, competitive with the deepest ore tier.",
    category=ItemCategory.WEAPON, max_stack=1,
    rarity=ItemRarity.EPIC, value=170, damage=30.0, speed=3.2,
    max_durability=450, icon_key="slime_king_fang",
    is_weapon=True, is_ranged=False,
))

_register(ItemDef(
    id="slime_king_bulwark", name="Bulwark of the Slime King",
    description="A chestpiece forged from the Slime King's Core and Steel. A farmable body armor, competitive with the deepest ore tier.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.EPIC, value=175, max_durability=420,
    icon_key="slime_king_bulwark", equip_slot="body", defense=18.0,
))


# --- Biome exclusive mobs (Snow Frost Hopper / Jungle Swamp Mosquito) ---
# Drops plus one craft each so farming them isn't a dead end. frost_arrows
# is ammo both Warrior and Summoner can spend; wing_charm is a light
# accessory that doesn't invent a new ammo type.

_register(ItemDef(
    id="frost_shard", name="Frost Shard",
    description="A sliver of permafrost shed by a Frost Hopper.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=4, icon_key="frost_shard",
))

_register(ItemDef(
    id="mosquito_wing", name="Mosquito Wing",
    description="A translucent wing torn from a Jungle mosquito.",
    category=ItemCategory.MATERIAL, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.COMMON, value=3, icon_key="mosquito_wing",
))

_register(ItemDef(
    id="wing_charm", name="Wing Charm",
    description="A light charm woven from mosquito wings. Equip in the accessory slot -- faintly lights nearby tiles.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=18, max_durability=None,
    icon_key="wing_charm", equip_slot="accessory", light_emit=4,
))

# --- Dead-end material sinks (cactus fiber besides cactus-arrows, duskwing
# feathers besides the rare anklets, gem bars besides the Arcane Bar) plus
# a craftable potion so slime gel and apples combine into a mid-heal
# consumable. Stats stay between wood and iron / well below Voidsteel --
# these fill obtain-path holes, they are not a new power tier. ---

_register(ItemDef(
    id="healing_potion", name="Healing Potion",
    description="A mixed tonic of fruit and slime gel. Press F to drink and restore 40 HP -- more than a raw apple, without matching late-game food.",
    category=ItemCategory.CONSUMABLE, max_stack=DEFAULT_STACK_SIZE,
    rarity=ItemRarity.UNCOMMON, value=8, icon_key="healing_potion", heal_amount=40.0,
))

_register(ItemDef(
    id="cactus_jerkin", name="Cactus Jerkin",
    description="A desert-stitched chestpiece of cactus fiber over a wood frame. Stronger than wood armor, weaker than iron -- a reason to gather cactus besides arrows.",
    category=ItemCategory.ARMOR, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=36, max_durability=180,
    icon_key="cactus_jerkin", equip_slot="body", defense=8.0,
))

_register(ItemDef(
    id="feather_charm", name="Feather Charm",
    description="A light charm bound from duskwing feathers. Equip in the accessory slot for a small move-speed boost.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.COMMON, value=12, max_durability=None,
    icon_key="feather_charm", equip_slot="accessory",
    move_speed_bonus=0.5, defense=1.0,
))

_register(ItemDef(
    id="topaz_ring", name="Topaz Ring",
    description="A ring set with a Topaz Bar. Equip in the accessory slot for a chance to land critical hits -- a use for Topaz Bars besides the Arcane Bar.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=48, max_durability=None,
    icon_key="topaz_ring", equip_slot="accessory", crit_chance=0.05,
))

_register(ItemDef(
    id="sapphire_ring", name="Sapphire Ring",
    description="A ring set with a Sapphire Bar. Equip in the accessory slot for extra defense and a modest worn light -- a use for Sapphire Bars besides the Arcane Bar.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=48, max_durability=None,
    icon_key="sapphire_ring", equip_slot="accessory", defense=4.0, light_emit=8,
))

_register(ItemDef(
    id="emerald_ring", name="Emerald Ring",
    description="A ring set with an Emerald Bar. Equip in the accessory slot for a move-speed boost -- a use for Emerald Bars besides the Arcane Bar.",
    category=ItemCategory.ACCESSORY, max_stack=1,
    rarity=ItemRarity.UNCOMMON, value=48, max_durability=None,
    icon_key="emerald_ring", equip_slot="accessory", move_speed_bonus=0.8,
))


def get(item_id: str) -> ItemDef:
    return _ITEMS[item_id]


def all_items() -> Dict[str, ItemDef]:
    return dict(_ITEMS)


def by_category(category: ItemCategory) -> Dict[str, ItemDef]:
    return {item_id: item for item_id, item in _ITEMS.items() if item.category == category}
