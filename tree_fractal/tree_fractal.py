import math
import numpy as np
import matplotlib.pyplot as plt


def _draw_tree(order, x1, y1, angle, angle_increment):
    new_angle = angle * math.pi / 180

    if order == 1:
        return
    else:
        x2 = (x1 + int(np.round(math.sin(new_angle) * order * 10)))
        y2 = (y1 + int(np.round(math.cos(new_angle) * order * 10)))

        plt.plot([x1, x2], [y1, y2])

        _draw_tree(order-1, x2, y2, angle + angle_increment, angle_increment)
        _draw_tree(order-1, x2, y2, angle - angle_increment, angle_increment)


def draw_tree(order, angle_increment=30):
    _draw_tree(order, 300, 300, 0, angle_increment)


draw_tree(12, 20)
plt.show()
