import math
import panda3d

from direct.particles import Particles
from panda3d.physics import BaseParticleRenderer,\
     PointParticleRenderer, BaseParticleEmitter
from ..assets.particle_system import ParticleSystem


DEFAULT_TEXTURE_NAME = "AAAWHITE"


def load_particle_system_from_block(name_prefix, psys_block, textures):
    enables = psys_block.enables
    
    texname = psys_block.p_texname if enables.p_texname else None
    texture = None if texname is None else textures.get(
        texname, textures.get(DEFAULT_TEXTURE_NAME)
        )
    psys_flags = {
        n: bool(psys_block.flags[n])
        for n in psys_block.flags.NAME_MAP
        if psys_block.flag_enables[n]
        }
    psys_data = dict(
        preset    = (psys_block.preset.enum_name if enables.preset else None),
        p_color   = [],
        p_rgb     = bool(enables.p_rgb),
        p_alpha   = bool(enables.p_alpha),
        texture   = texture,
    )
    for i, color in enumerate(psys_block.p_color):
        r, g, b, a = tuple((v / 255) for v in color)
        if not enables.p_rgb:
            r = g = b = 1.0

        if not enables.p_alpha:
            a = 1.0

        psys_data["p_color"].append([r, g, b, a])

    psys_data.update({
        name: psys_block[name]
        for name in ("max_p", "max_dir", "max_pos", "e_angle", "e_rate_rand",
                     "p_gravity", "p_drag", "p_speed", "p_texcnt", "e_delay")
        if enables[name]
        })
    psys_data.update({
        name: tuple(psys_block[name])
        for name in ("e_life", "p_life", "e_rate", "p_width")
        if enables[name]
        })
    if enables.e_dir:
        psys_data["e_dir"] = (
            psys_block.e_dir[0],
            psys_block.e_dir[2],
            psys_block.e_dir[1]
            )
    if enables.e_vol:
        psys_data["e_vol"] = (
            psys_block.e_vol[0],
            psys_block.e_vol[2],
            psys_block.e_vol[1]
            )

    def config_loader(peffect, flags=psys_flags, data=psys_data):
        peffect.reset()
        peffect.setPos(0.000, 0.000, 0.000)
        peffect.setHpr(0.000, 0.000, 0.000)
        peffect.setScale(1.000, 1.000, 1.000)

        peffect.renderParent.setTransparency(
            panda3d.core.TransparencyAttrib.MDual if flags.get("fb_add") else
            panda3d.core.TransparencyAttrib.MDual if flags.get("fb_mul") else
            panda3d.core.TransparencyAttrib.MAlpha
            )
        peffect.renderParent.setDepthTest(not flags.get("no_z_test"))
        peffect.renderParent.setDepthWrite(False)

        for i in range(4 if "e_rate" in data else 1):
            part = Particles.Particles(f'p{i}')

            e_rate_rand = psys_data.get("e_rate_rand", 1)
            e_angle = psys_data.get("e_angle", 0)
            e_dir   = psys_data.get("e_dir",   [0, 0, 1])
            e_vol   = psys_data.get("e_vol",   None)
            e_life  = psys_data.get("e_life",  [0, 0])
            p_life  = psys_data.get("p_life",  [0, 0])
            width   = psys_data.get("p_width", [1]*(i+1))[i] / 2
            e_rate  = psys_data.get("e_rate",  [e_rate_rand]*(i+1))[i]
            p_color = psys_data.get("p_color", [(1, 1, 1, 1)]*(i+1))[i]
            texture = psys_data.get("texture")

            # Particles parameters
            part.setFactory("PointParticleFactory")
            if texture:
                part.setRenderer("SpriteParticleRenderer")
            else:
                part.setRenderer("PointParticleRenderer")

            if e_vol:
                part.setEmitter("BoxEmitter")
            else:
                part.setEmitter("PointEmitter")

            if not e_rate:
                continue

            litter_size = int(math.ceil(e_rate / 30))
            birth_rate  = litter_size / e_rate

            part.setPoolSize(psys_data.get("max_p", 1000))
            part.setBirthRate(birth_rate)
            part.setLitterSize(litter_size)
            part.setLitterSpread(0)
            # TODO: figure out what to do with these 3
            part.setLocalVelocityFlag(1)
            part.setSystemLifespan(0)
            part.setSystemGrowsOlderFlag(0)

            fact, rend, emit = part.factory, part.renderer, part.emitter

            # Factory parameters
            fact.setLifespanBase(max(0, min(p_life)))
            fact.setLifespanSpread(max(0, max(p_life) - min(p_life)))
            fact.setMassBase(1)
            fact.setMassSpread(0)
            fact.setTerminalVelocityBase(0)
            fact.setTerminalVelocitySpread(0)

            # Renderer parameters
            rend.setAlphaMode(BaseParticleRenderer.PR_ALPHA_USER)  # ????
            rend.setUserAlpha(2.0)  # account for signed alpha
            if texture:
                rend.setTexture(texture.p3d_texture)
                rend.setAlphaDisable(bool(flags.get("no_tex_a")))
                rend.setSize(width, width)
                rend.setColor(panda3d.core.LVector4(*p_color))
                rend.setXScaleFlag(False)
                rend.setYScaleFlag(False)
                rend.setAnimAngleFlag(False)
                rend.setInitialXScale(1)
                rend.setFinalXScale(1)
                rend.setInitialYScale(1)
                rend.setFinalYScale(1)
                rend.setNonanimatedTheta(0)
            else:
                rend.setPointSize(width)
                rend.setStartColor(panda3d.core.LVector4(*p_color))
                rend.setBlendType(PointParticleRenderer.PointParticleBlendType.ONE_COLOR)

            if flags.get("fb_mul"):
                rend.setColorBlendMode(
                    panda3d.core.ColorBlendAttrib.MAdd,
                    panda3d.core.ColorBlendAttrib.OFbufferColor,
                    panda3d.core.ColorBlendAttrib.OZero,
                    )
            elif flags.get("fb_add"):
                rend.setColorBlendMode(
                    panda3d.core.ColorBlendAttrib.MAdd,
                    panda3d.core.ColorBlendAttrib.OIncomingAlpha,
                    panda3d.core.ColorBlendAttrib.OOne,
                    )

            # Emitter parameters
            emit.setEmissionType(BaseParticleEmitter.ETEXPLICIT)
            emit.setExplicitLaunchVector(panda3d.core.LVector3(*e_dir))
            emit.setAmplitude(psys_data.get("p_speed", 0))
            if e_vol:
                emit.setMinBound(panda3d.core.LVector3(*(-abs(v) for v in e_vol)))
                emit.setMaxBound(panda3d.core.LVector3(*( abs(v) for v in e_vol)))

            # TODO: account for e_delay, p_drag, p_gravity, e_angle

            peffect.addParticles(part)

    psys = ParticleSystem(
        name=name_prefix + psys_block.id.enum_name,
        config_loader=config_loader, unique_instances=False
        )
    return psys


def load_particle_systems_from_worlds_tag(worlds_tag, world_name="", textures=()):
    if not textures:
        textures = {}

    psys_by_name = {}
    name_prefix = world_name.upper() + "PSYS"
    for psys_block in worlds_tag.data.particle_systems:
        psys = load_particle_system_from_block(name_prefix, psys_block, textures)
        if psys.name in psys_by_name:
            print(f"Warning: Duplicate particle system '{psys.name}' detected. Skipping.")
        else:
            psys_by_name[psys.name] = psys

    return psys_by_name


def load_particle_systems_from_animations_tag(anim_tag, resource_name="", textures=()):
    if not textures:
        textures = {}

    psys_by_index = []
    name_prefix = resource_name.upper() + "PSYS"
    try:
        psys_array = list(anim_tag.data.particle_systems)
    except TypeError:
        psys_array = []

    for psys_block in psys_array:
        psys = load_particle_system_from_block(name_prefix, psys_block, textures)
        psys_by_index.append(psys)

    return psys_by_index
