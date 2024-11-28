import math
import matplotlib.pyplot as plt


def _draw_tree(level, x1, y1, angle, angle_increment):
    if level == 1:
        return
    else:
        angle_rad = angle * math.pi / 180
        x2 = x1 + math.sin(angle_rad) * level * 10
        y2 = y1 + math.cos(angle_rad) * level * 10

        plt.plot([x1, x2], [y1, y2])

        _draw_tree(level - 1, x2, y2, angle + angle_increment, angle_increment)
        _draw_tree(level - 1, x2, y2, angle - angle_increment, angle_increment)


def draw_tree(levels=8, angle_increment=30):
    _draw_tree(levels, 0, 0, 0, angle_increment)


draw_tree(levels=12, angle_increment=25)
plt.show()
