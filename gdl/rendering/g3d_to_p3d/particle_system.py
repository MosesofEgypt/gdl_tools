import math
import panda3d

from direct.particles import Particles
from panda3d.physics import BaseParticleRenderer,\
     PointParticleRenderer, BaseParticleEmitter
from ..assets.particle_system import ParticleSystem


DEFAULT_TEXTURE_NAME = "AAAWHITE"
DEFAULT_PHASE_LIFE   = 1.0
DEFAULT_EMIT_RATE    = 30
DEFAULT_PART_WIDTH   = 1.0


def load_particle_system_from_block(name_prefix, psys_block, textures,
                                    unique_instances=False):
    enables = psys_block.enables
    
    texname = psys_block.part_texname if enables.part_texname else None
    texture = None if texname is None else textures.get(
        texname, textures.get(DEFAULT_TEXTURE_NAME)
        )
    emit_life = (
        tuple(max(0, v) for v in psys_block.emit_life)
        if enables.emit_life else
        (DEFAULT_PHASE_LIFE, DEFAULT_PHASE_LIFE)
        )
    psys_flags = {
        n: bool(psys_block.flags[n])
        for n in psys_block.flags.NAME_MAP
        if psys_block.flag_enables[n]
        }
    psys_data = dict(
        texture        = texture,
        max_particles  = psys_block.max_particles  if enables.max_particles  else 10000,
        max_dir        = psys_block.max_dir        if enables.max_dir        else 10000, # TODO: determine purpose
        max_pos        = psys_block.max_pos        if enables.max_pos        else 10000, # TODO: determine purpose
        emit_angle     = psys_block.emit_angle     if enables.emit_angle     else 0,
        emit_rate_rand = psys_block.emit_rate_rand if enables.emit_rate_rand else 0, # TODO: determine purpose
        emit_delay     = psys_block.emit_delay     if enables.emit_delay     else 0, # TODO: determine purpose
        part_gravity   = psys_block.part_gravity   if enables.part_gravity   else 0,
        part_speed     = psys_block.part_speed     if enables.part_speed     else 0,
        part_drag      = psys_block.part_drag      if enables.part_drag      else 0, # TODO: determine purpose
        emit_length    = sum(emit_life),
        phase_b_start  = emit_life[0],
        emit_dir = (
            psys_block.emit_dir[0],
            psys_block.emit_dir[2],
            psys_block.emit_dir[1]
            ) if enables.emit_dir else (0, 0, 1),
        emit_vol = (
            psys_block.emit_vol[0],
            psys_block.emit_vol[2],
            psys_block.emit_vol[1]
            ) if enables.emit_vol else None,
        )

    for phase in ("phase_a", "phase_b"):
        psys_data[phase] = dict()

        for point in ("in", "out"):
            emit_rate  = psys_block.emit_rate[f"{phase}_{point}"]
            part_width = psys_block.part_width[f"{phase}_{point}"]
            b, g, r, a = psys_block.part_color[f"{phase}_{point}"]

            if not enables.part_rgb:   b = g = r = 255
            if not enables.part_alpha: a = 255

            psys_data[phase][f"{point}_color"] = (r/255, g/255, b/255, a/255)
            psys_data[phase][f"{point}_rate"]  = emit_rate  if enables.emit_rate  else DEFAULT_EMIT_RATE
            psys_data[phase][f"{point}_width"] = part_width if enables.part_width else DEFAULT_PART_WIDTH

    def config_loader(peffect, flags=psys_flags, data=psys_data):
        peffect.reset()
        peffect.setPos(0.000, 0.000, 0.000)
        peffect.setHpr(0.000, 0.000, 0.000)
        peffect.setScale(1.000, 1.000, 1.000)
        return

        peffect.renderParent.setTransparency(
            panda3d.core.TransparencyAttrib.MDual
            if (flags.get("fb_add") or flags.get("fb_mul")) else
            panda3d.core.TransparencyAttrib.MAlpha
            )
        peffect.renderParent.setDepthTest(not flags.get("no_z_test"))
        peffect.renderParent.setDepthWrite(False)

        part = Particles.Particles()

        emit_rate_rand = psys_data.get("emit_rate_rand", 1)
        emit_angle = psys_data.get("emit_angle", 0)
        emit_dir   = psys_data.get("emit_dir",   [0, 0, 1])
        emit_vol   = psys_data.get("emit_vol",   None)
        emit_life  = psys_data.get("emit_life",  [0, 0])
        part_life  = psys_data.get("part_life",  [0, 0])
        width      = psys_data.get("part_width", [1]*(i+1))[i] / 2
        emit_rate  = psys_data.get("emit_rate",  [emit_rate_rand]*(i+1))[i]
        part_color = psys_data.get("part_color", [(1, 1, 1, 1)]*(i+1))[i]
        texture = psys_data.get("texture")

        # Particles parameters
        part.setFactory("PointParticleFactory")
        if texture:
            part.setRenderer("SpriteParticleRenderer")
        else:
            part.setRenderer("PointParticleRenderer")

        part.setEmitter("DiscEmitter")

        litter_size = int(math.ceil(emit_rate / 30))
        birth_rate  = litter_size / emit_rate

        part.setPoolSize(psys_data["max_particles"])
        part.setBirthRate(birth_rate)
        part.setLitterSize(litter_size)
        part.setLitterSpread(0)
        # TODO: figure out what to do with these 3
        part.setLocalVelocityFlag(1)
        part.setSystemLifespan(0)
        part.setSystemGrowsOlderFlag(0)

        fact, rend, emit = part.factory, part.renderer, part.emitter

        # TODO: implement properly using e_life and p_life

        # Factory parameters
        fact.setLifespanBase(max(0, min(part_life)))
        fact.setLifespanSpread(max(0, max(part_life) - min(part_life)))
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
            rend.setColor(panda3d.core.LVector4(*part_color))
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
            rend.setStartColor(panda3d.core.LVector4(*part_color))
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
        emit.setExplicitLaunchVector(panda3d.core.LVector3(*emit_dir))
        emit.setAmplitude(psys_data.get("part_speed", 0))

        # TODO: account for e_delay, p_drag, p_gravity, e_angle

        peffect.addParticles(part)

    psys = ParticleSystem(
        name=name_prefix + psys_block.id.enum_name,
        config_loader=config_loader, unique_instances=unique_instances
        )
    return psys


def load_particle_systems_from_worlds_tag(
        worlds_tag, world_name="", textures=(), unique_instances=False
        ):
    if not textures:
        textures = {}

    psys_by_name = {}
    name_prefix = world_name.upper() + "PSYS"
    for psys_block in worlds_tag.data.particle_systems:
        psys = load_particle_system_from_block(
            name_prefix, psys_block, textures, unique_instances
            )
        if psys.name in psys_by_name:
            print(f"Warning: Duplicate particle system '{psys.name}' detected. Skipping.")
        else:
            psys_by_name[psys.name] = psys

    return psys_by_name


def load_particle_systems_from_animations_tag(
        anim_tag, resource_name="", textures=(), unique_instances=False
        ):
    if not textures:
        textures = {}

    psys_by_index = []
    name_prefix = resource_name.upper() + "PSYS"
    try:
        psys_array = list(anim_tag.data.particle_systems)
    except TypeError:
        psys_array = []

    for psys_block in psys_array:
        psys = load_particle_system_from_block(
            name_prefix, psys_block, textures, unique_instances
            )
        psys_by_index.append(psys)

    return psys_by_index
