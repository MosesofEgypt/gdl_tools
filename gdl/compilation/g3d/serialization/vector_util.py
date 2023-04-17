from math import atan2, acos, cos, sin, sqrt, pi, isinf, isnan

ACOS_NEG_ONE = acos(-1)
ACOS_ONE     = acos(1)


def dot_product(v0, v1):
    return sum(a*b for a, b in zip(v0, v1))


def cross_product(ray_a, ray_b):
    return ((ray_a[1]*ray_b[2] - ray_a[2]*ray_b[1],
             ray_a[2]*ray_b[0] - ray_a[0]*ray_b[2],
             ray_a[0]*ray_b[1] - ray_a[1]*ray_b[0]))

def gdl_normal_to_quaternion(ni, nj, nk):
    # NOTE: quaternion is returned in the form i, j, k, w
    r = (
        ACOS_NEG_ONE if nj <= -1.0 else
        ACOS_ONE     if nj >=  1.0 else
        acos(nj)
        )
    if isnan(ni) or isnan(nk) or (isinf(ni) and isinf(nk)):
        y = 0
    else:
        y = atan2(ni, nk)

    # rotations occur in this order:
    #   yaw:  around y axis from +z to +x
    #   roll: around z axis from +x to +y
    c0, c1 = cos(y / 2), cos(r / 2)
    s0, s1 = sin(y / 2), sin(r / 2)
    return -c0*s1, s0*c1, s0*s1, c0*c1


cos_angle_between_vectors = dot_product


def rotate_vector_by_quaternion(v, q):
    # NOTE: quaternion is expected to be in form i, j, k, w
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
