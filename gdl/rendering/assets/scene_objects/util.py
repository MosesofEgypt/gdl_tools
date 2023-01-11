from math import cos, sin

def gdl_euler_to_quaternion(r, h, p):
    '''Returns quaternion as w, i, j, k'''
    c0, c1, c2 = cos(r / 2), cos(h / 2), cos(-p / 2)
    s0, s1, s2 = sin(r / 2), sin(h / 2), sin(-p / 2)
    return (c0*c1*c2 - s0*s1*s2,
            s0*s1*c2 + c0*c1*s2,
            s0*c1*c2 + c0*s1*s2,
            c0*s1*c2 - s0*c1*s2)
