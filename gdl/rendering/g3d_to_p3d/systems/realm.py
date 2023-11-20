from ...assets import constants as c
from ...assets.systems.realm import Realm, RealmLevel


def load_realm_from_wdata_tag(wdata_tag):
    world_lump = wdata_tag.get_lump_of_type("wrld")
    level_lump = wdata_tag.get_lump_of_type("levl")
    enemy_lump = wdata_tag.get_lump_of_type("enmy")
    if None in (world_lump, level_lump, enemy_lump):
        return None

    try:
        world_data = world_lump[0]
    except IndexError:
        return None

    enemies = {}
    for enemy in enemy_lump:
        enemies[len(enemies)] = dict(
            type    = enemy.type.enum_name.lower(),
            subtype = enemy.subtype.enum_name.lower(),
            name    = enemy.name.lower(),
            audio   = enemy.audname,
            )

    realm_levels = []
    for level in level_lump:
        enemy_type_boss      = ""
        enemy_type_golem     = ""
        enemy_type_general   = ""
        enemy_type_gargoyle  = ""
        enemy_type_aux       = ""
        enemy_type_gen_small = ""
        enemy_type_gen_large = ""
        enemy_types_special  = []
        special_max_level    = 0
        for i in level.enemy_types:
            enemy = enemies.get(i)
            if enemy is None:
                continue

            folder_name = c.ENEMY_TYPE_TO_DIRNAME.get(enemy["type"], "")
            if enemy["type"] == "gargoyle":
                folder_name = c.MONSTER_NAME_GAR % enemy["name"]
            elif enemy["type"] in ("general", "golem"):
                folder_name = world_data.wave_name
            elif enemy["subtype"] == "aux":
                folder_name = c.MONSTER_NAME_AUX % folder_name
            elif enemy["subtype"].startswith("special_l"):
                special_max_level = int(enemy["subtype"][-1])
                folder_name = c.MONSTER_NAME_NUM % (
                    folder_name, special_max_level
                    )

            if enemy["type"] == "general":
                enemy_type_general = folder_name
            elif enemy["type"] == "golem":
                enemy_type_golem = folder_name
            elif enemy["type"] == "gargoyle":
                enemy_type_gargoyle = folder_name
            elif enemy["subtype"] == "main_boss":
                enemy_type_boss = folder_name
            elif enemy["subtype"] == "ankle_biter":
                enemy_type_gen_small = folder_name
            elif enemy["subtype"] in ("generator_pri", "generator_sec"):
                enemy_type_gen_large = folder_name
            elif "special" in enemy["subtype"]:
                enemy_types_special.append(folder_name)

        realm_levels.append(RealmLevel(
            name=level.name, title=level.title,
            boss_type=level.boss_type.data,
            enemy_type_boss      = enemy_type_boss,
            enemy_type_golem     = enemy_type_golem,
            enemy_type_general   = enemy_type_general,
            enemy_type_gargoyle  = enemy_type_gargoyle,
            enemy_type_aux       = enemy_type_aux,
            enemy_type_gen_small = enemy_type_gen_small,
            enemy_type_gen_large = enemy_type_gen_large,
            enemy_types_special  = enemy_types_special,
            special_max_level    = special_max_level,
            ))

    return Realm(
        name=world_data.wave_name,
        type=world_data.type.enum_name,
        levels=realm_levels
        )
