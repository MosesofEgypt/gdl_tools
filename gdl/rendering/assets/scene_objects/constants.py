
MONSTER_NAME_GAR = "GAR_%s"
MONSTER_NAME_AUX = "%sAUX"
MONSTER_NAME_NUM = "%s%d"

ACTOR_NAME_BOSSGEN      = "BOSSGEN"
OBJECT_NAME_GEN_SPECIAL = "GEN_SPECIAL%d"
OBJECT_NAME_GEN         = "GEN_%s%d"

STATUE_NAME_GAR = "GAR_STATUE"
STATUE_NAME_GOL = "GOL_STATUE"
STATUE_NAME_DEATH1 = "DEATHSTATUE1"
STATUE_NAME_DEATH2 = "DEATHSTATUE2"

OBJECT_NAME_BOMB      = "BOMB"
OBJECT_NAME_BOMB00    = "BOMB00"
OBJECT_NAME_HEAD      = "HEAD"
OBJECT_NAME_L_WRIST   = "L_WRIST"
OBJECT_NAME_R_WRIST   = "R_WRIST"
OBJECT_NAME_LEFTHAND  = "LEFTHAND"
OBJECT_NAME_RIGHTHAND = "RIGHTHAN"
OBJECT_NAME_WEAP_HOLD = "WEAP_HOLD"
OBJECT_NAME_WEAP_HD   = "WEAP_%s_HD%d"
OBJECT_NAME_SHADOW    = "SHADOWL1"
OBJECT_NAME_SHADOW1   = "SHADOW1L1"
OBJECT_NAME_SHADOW2   = "SHADOW2L1"
OBJECT_NAME_SHADOW3   = "SHADOW3L1"

COLL_TYPE_NULL      = -1
COLL_TYPE_NONE      = 0x00
COLL_TYPE_CYLINDER  = 0x01
COLL_TYPE_SPHERE    = 0x02
COLL_TYPE_BOX       = 0x03
COLL_TYPE_OBJECT    = 0x04

ITEM_TYPE_RANDOM        = -1
ITEM_TYPE_NONE          = 0x00
ITEM_TYPE_POWERUP       = 0x01
ITEM_TYPE_CONTAINER     = 0x02
ITEM_TYPE_GENERATOR     = 0x03
ITEM_TYPE_ENEMY         = 0x04
ITEM_TYPE_TRIGGER       = 0x05
ITEM_TYPE_TRAP          = 0x06
ITEM_TYPE_DOOR          = 0x07
ITEM_TYPE_DAMAGE_TILE   = 0x08
ITEM_TYPE_EXIT          = 0x09
ITEM_TYPE_OBSTACLE      = 0x0A
ITEM_TYPE_TRANSPORTER   = 0x0B
ITEM_TYPE_ROTATOR       = 0x0C
ITEM_TYPE_SOUND         = 0x0D

ITEM_SUBTYPE_NONE       = 0x00
ITEM_SUBTYPE_GOLD       = 0x01
ITEM_SUBTYPE_KEY        = 0x02
ITEM_SUBTYPE_FOOD       = 0x03
ITEM_SUBTYPE_POTION     = 0x04
ITEM_SUBTYPE_WEAPON     = 0x05
ITEM_SUBTYPE_ARMOR      = 0x06
ITEM_SUBTYPE_SPEED      = 0x07
ITEM_SUBTYPE_MAGIC      = 0x08
ITEM_SUBTYPE_SPECIAL    = 0x09
ITEM_SUBTYPE_RUNESTONE  = 0x0A
ITEM_SUBTYPE_BOSSKEY    = 0x0B
ITEM_SUBTYPE_OBELISK    = 0x0C
ITEM_SUBTYPE_QUEST      = 0x0D
ITEM_SUBTYPE_SCROLL     = 0x0E
ITEM_SUBTYPE_GEMSTONE   = 0x0F
ITEM_SUBTYPE_FEATHER    = 0x10

ITEM_SUBTYPE_BRIDGE_PAD         = 0x14
ITEM_SUBTYPE_DOOR_PAD           = 0x15
ITEM_SUBTYPE_BRIDGE_SWITCH      = 0x16
ITEM_SUBTYPE_DOOR_SWITCH        = 0x17
ITEM_SUBTYPE_ACTIVATOR_SWITCH   = 0x18
ITEM_SUBTYPE_ELEVATOR_PAD       = 0x19
ITEM_SUBTYPE_ELEVATOR_SWITCH    = 0x1A
ITEM_SUBTYPE_LIFT_PAD           = 0x1B
ITEM_SUBTYPE_LIFT_START         = 0x1C
ITEM_SUBTYPE_LIFT_END           = 0x1D
ITEM_SUBTYPE_NO_WEAPON_COLLIDER = 0x1E
ITEM_SUBTYPE_SHOOT_TRIGGER      = 0x1F

ITEM_SUBTYPE_ROCK_FALL      = 0x28
ITEM_SUBTYPE_SAFE_ROCK      = 0x29
ITEM_SUBTYPE_WALL           = 0x2A
ITEM_SUBTYPE_BARREL         = 0x2B
ITEM_SUBTYPE_BARREL_EXPLODE = 0x2C
ITEM_SUBTYPE_BARREL_POISON  = 0x2D
ITEM_SUBTYPE_CHEST          = 0x2E
ITEM_SUBTYPE_CHEST_SILVER   = 0x2F
ITEM_SUBTYPE_CHEST_GOLD     = 0x30
ITEM_SUBTYPE_LEAF_FALL      = 0x31
ITEM_SUBTYPE_SECRET         = 0x32
ITEM_SUBTYPE_ROCK_FLY       = 0x33
ITEM_SUBTYPE_SHOOT_FALL     = 0x34
ITEM_SUBTYPE_ROCK_SINK      = 0x35

# TODO: figure these out
OBSTACLE_TYPE_NONE = 0x00

COLL_TYPES = frozenset((
    COLL_TYPE_NULL, COLL_TYPE_NONE, COLL_TYPE_CYLINDER,
    COLL_TYPE_SPHERE, COLL_TYPE_BOX, COLL_TYPE_OBJECT
    ))

ITEM_TYPES = frozenset((
    ITEM_TYPE_RANDOM, ITEM_TYPE_NONE, ITEM_TYPE_POWERUP,
    ITEM_TYPE_CONTAINER, ITEM_TYPE_GENERATOR, ITEM_TYPE_ENEMY,
    ITEM_TYPE_TRIGGER, ITEM_TYPE_TRAP, ITEM_TYPE_DOOR,
    ITEM_TYPE_DAMAGE_TILE, ITEM_TYPE_EXIT, ITEM_TYPE_OBSTACLE,
    ITEM_TYPE_TRANSPORTER, ITEM_TYPE_ROTATOR, ITEM_TYPE_SOUND
    ))

ITEM_SUBTYPES = frozenset((
    ITEM_SUBTYPE_NONE, ITEM_SUBTYPE_GOLD, ITEM_SUBTYPE_KEY,
    ITEM_SUBTYPE_FOOD, ITEM_SUBTYPE_POTION, ITEM_SUBTYPE_WEAPON,
    ITEM_SUBTYPE_ARMOR, ITEM_SUBTYPE_SPEED, ITEM_SUBTYPE_MAGIC,
    ITEM_SUBTYPE_SPECIAL, ITEM_SUBTYPE_RUNESTONE, ITEM_SUBTYPE_BOSSKEY,
    ITEM_SUBTYPE_OBELISK, ITEM_SUBTYPE_QUEST, ITEM_SUBTYPE_SCROLL,
    ITEM_SUBTYPE_GEMSTONE, ITEM_SUBTYPE_FEATHER,

    ITEM_SUBTYPE_BRIDGE_PAD, ITEM_SUBTYPE_DOOR_PAD,
    ITEM_SUBTYPE_BRIDGE_SWITCH, ITEM_SUBTYPE_DOOR_SWITCH,
    ITEM_SUBTYPE_ACTIVATOR_SWITCH, ITEM_SUBTYPE_ELEVATOR_PAD,
    ITEM_SUBTYPE_ELEVATOR_SWITCH, ITEM_SUBTYPE_LIFT_PAD,
    ITEM_SUBTYPE_LIFT_START, ITEM_SUBTYPE_LIFT_END,
    ITEM_SUBTYPE_NO_WEAPON_COLLIDER, ITEM_SUBTYPE_SHOOT_TRIGGER,

    ITEM_SUBTYPE_ROCK_FALL, ITEM_SUBTYPE_SAFE_ROCK, ITEM_SUBTYPE_WALL,
    ITEM_SUBTYPE_BARREL, ITEM_SUBTYPE_BARREL_EXPLODE,
    ITEM_SUBTYPE_BARREL_POISON, ITEM_SUBTYPE_CHEST,
    ITEM_SUBTYPE_CHEST_SILVER, ITEM_SUBTYPE_CHEST_GOLD,
    ITEM_SUBTYPE_LEAF_FALL, ITEM_SUBTYPE_SECRET,
    ITEM_SUBTYPE_ROCK_FLY, ITEM_SUBTYPE_SHOOT_FALL, ITEM_SUBTYPE_ROCK_SINK
    ))

OBSTACLE_SUBTYPES = frozenset((
    OBSTACLE_TYPE_NONE,
    ))
