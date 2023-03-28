from math import cos, sin

def gdl_euler_to_quaternion(y, p, r):
    '''Returns quaternion as w, i, j, k'''
    c0, c1, c2 = cos(-y/2), cos(p/2), cos(-r/2)
    s0, s1, s2 = sin(-y/2), sin(p/2), sin(-r/2)
    
    c0c1 = c0*c1
    c0s1 = c0*s1
    s0c1 = s0*c1
    s0s1 = s0*s1

    return (
        c0c1*c2 - s0s1*s2, c0c1*s2 + s0s1*c2,
	s0c1*c2 + c0s1*s2, c0s1*c2 - s0c1*s2
        )
