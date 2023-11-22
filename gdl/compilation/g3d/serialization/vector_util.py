from math import cos, sin, sqrt, pi


def dot_product(v0, v1):
    return sum(a*b for a, b in zip(v0, v1))


def cross_product(ray_a, ray_b):
    return ((ray_a[1]*ray_b[2] - ray_a[2]*ray_b[1],
             ray_a[2]*ray_b[0] - ray_a[0]*ray_b[2],
             ray_a[0]*ray_b[1] - ray_a[1]*ray_b[0]))


cos_angle_between_vectors = dot_product


def rotate_vector_by_quaternion(v, q):
    vm_sq = v[0]**2 + v[1]**2 + v[2]**2
    if not vm_sq:
        return (0, 0, 0)

    vm = sqrt(vm_sq)
    v1 = [q[0], q[1], q[2]]
    v2 = [v[0], v[1], v[2]]
    v3 = cross_product(v1, v2)

    v1m = 2 * dot_product(v1, v)
    v2m = q[3]**2 - dot_product(v1, v1)
    v3m = 2 * q[3]

    vr = (
        v1[0]*v1m + v2[0]*v2m + v3[0]*v3m,
        v1[1]*v1m + v2[1]*v2m + v3[1]*v3m,
        v1[2]*v1m + v2[2]*v2m + v3[2]*v3m,
        )
    vrm_sq = vr[0]**2 + vr[1]**2 + vr[2]**2
    if not vrm_sq:
        return (0, 0, 0)

    scale = vm / sqrt(vrm_sq)
    return (vr[0] * scale, vr[1] * scale, vr[2] * scale)


def point_inside_2d_triangle(p, v0, v1, v2):
    # didn't want to have to figure this out, so
    # I borrowed the code from stackoverflow:
    #   https://stackoverflow.com/a/9755252
    dx_p0 =  p[0] - v0[0]
    dy_p0 =  p[1] - v0[1]
    dx_10 = v1[0] - v0[0]
    dy_10 = v1[1] - v0[1]
    dx_20 = v2[0] - v0[0]
    dy_20 = v2[1] - v0[1]
    sign = dx_10*dy_p0 > dy_10*dx_p0

    if (dx_20*dy_p0 > dy_20*dx_p0) == sign:
        return False

    dx_p1 =  p[0] - v1[0]
    dy_p1 =  p[1] - v1[1]
    dx_21 = v2[0] - v1[0]
    dy_21 = v2[1] - v1[1]
    return (dx_21*dy_p1 > dy_21*dx_p1) == sign


def unpack_norm_1555(norm_1555):
    xn  = (norm_1555&31)/15 - 1
    yn  = ((norm_1555>>5)&31)/15 - 1
    zn  = ((norm_1555>>10)&31)/15 - 1
    inv_mag = 1/(sqrt(xn*xn + yn*yn + zn*zn) + 0.0000001)
    return (xn*inv_mag, yn*inv_mag, zn*inv_mag)


def unpack_color_1555(color_1555):
    return (
        (color_1555&31)/31,        # red
        ((color_1555>>5)&31)/31,   # green
        ((color_1555>>10)&31)/31,  # blue
        ((color_1555>>15)&1)*1.0,  # alpha(always set?)
        )

NORM_1555_UNPACK_TABLE = tuple(map(unpack_norm_1555, range(0x8000)))
NORM_1555_UNPACK_TABLE += NORM_1555_UNPACK_TABLE  # double length for full 16bit range
COLOR_1555_UNPACK_TABLE = tuple(map(unpack_color_1555, range(0x10000)))
