import math
import time
import numpy as np
import matplotlib.pyplot as plt


def _draw(n_vertex=12, n_neighbor=3, gap=0, color='b'):
    vertices = [[np.cos(i * 2 * math.pi / n_vertex), np.sin(i * 2 * math.pi / n_vertex)] for i in range(n_vertex)]
    plt.plot([vertices[i][0] for i in range(n_vertex)], [vertices[i][1] for i in range(n_vertex)], f'{color}o')

    edges = [[i, (i + 1) % n_vertex] for i in range(n_vertex)]
    for edge in edges:
        plt.plot([vertices[edge[0]][0], vertices[edge[1]][0]], [vertices[edge[0]][1], vertices[edge[1]][1]], f'{color}-')

    for i in range(n_vertex):
        for j in range(2 + gap, n_neighbor + gap + 2):
            plt.plot([vertices[i][0], vertices[(i + j) % n_vertex][0]], [vertices[i][1], vertices[(i + j) % n_vertex][1]], f'{color}-')

    plt.axis('equal')


def draw(n_vertex=12, n_neighbor=3):
    for gap in range(3):
        _draw(n_vertex, n_neighbor, gap, 'b')
        time.sleep(0.2)
        _draw(n_vertex, n_neighbor, gap, 'w')


plt.figure(figsize=(10, 10))
draw(12, 2)
