import math

class Cal_function():
    def __init__(self):
        pass

    def angle_3pt(self, a, b, c):
        """
        คำนวณมุมจากจุด 3 จุด A-B-C
        """
        ax, ay = a
        bx, by = b
        cx, cy = c

        ab = (ax - bx, ay - by)
        cb = (cx - bx, cy - by)

        dot = ab[0] * cb[0] + ab[1] * cb[1]
        mag_ab = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
        mag_cb = math.sqrt(cb[0] ** 2 + cb[1] ** 2)

        if mag_ab * mag_cb == 0:
            return 0

        cos_angle = dot / (mag_ab * mag_cb)
        cos_angle = max(min(cos_angle, 1.0), -1.0)

        return math.degrees(math.acos(cos_angle))
    
    def distance(self, a, b):
        """
        คำนวณระยะทาง
        """
        ax, ay = a
        bx, by = b

        x_coord = bx - ax
        y_coord = by - by

        result = (x_coord ** 2) + (y_coord ** 2)

        distance = math.sqrt(result)

        return distance
    
    def degrees(self, a, b):
        ax, ay = a
        bx, by = b
        angle = math.degrees(math.atan2(
            bx - ax,
            by - ay
        ))

        return angle
    
