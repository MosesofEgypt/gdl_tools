from math import cos, sin, sqrt, pi


def dot_product(v0, v1):
    return sum(a*b for a, b in zip(v0, v1))


def cross_product(ray_a, ray_b):
    return ((ray_a[1]*ray_b[2] - ray_a[2]*ray_b[1],
             ray_a[2]*ray_b[0] - ray_a[0]*ray_b[2],
             ray_a[0]*ray_b[1] - ray_a[1]*ray_b[0]))


cos_angle_between_vectors = dot_product


def euler_to_quaternion(y, p, r):
    c0, c1, c2 = cos(y / 2), cos(p / 2), cos(r / 2)
    s0, s1, s2 = sin(y / 2), sin(p / 2), sin(r / 2)
    return (s0*s1*c2 + c0*c1*s2,
            s0*c1*c2 + c0*s1*s2,
            c0*s1*c2 - s0*c1*s2,
            c0*c1*c2 - s0*s1*s2)


def rotate_vector_by_quaternion(v, q):
    vm_sq = v[0]**2 + v[1]**2 + v[2]**2
    if not vm_sq:
        return (0, 0, 0)

    vm = sqrt(vm_sq)
    v1 = [q[0], q[1], q[2]]
    v2 = [v[0], v[1], v[2]]
    v3 = cross_product(v1, v)

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
