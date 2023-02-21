from math import cos, sin

def gdl_euler_to_quaternion(y, p, r):
    '''Returns quaternion as w, i, j, k'''
    c1, c2, c3 = cos(-y/2), cos(p/2), cos(-r/2)
    s1, s2, s3 = sin(-y/2), sin(p/2), sin(-r/2)
    
    c1c2 = c1*c2
    c1s2 = c1*s2
    s1c2 = s1*c2
    s1s2 = s1*s2

    return (
        c1c2*c3 - s1s2*s3, c1c2*s3 + s1s2*c3,
	s1c2*c3 + c1s2*s3, c1s2*c3 - s1c2*s3
        )
