import numpy as np
import matplotlib.pyplot as plt

# https://en.wikipedia.org/wiki/Sierpi%C5%84ski_triangle
# The Sierpinski triangle is a fractal that is generated by starting with an
# equilateral triangle and a random point inside the triangle then repeatedly
# choosing a random vertex and moving halfway towards that vertex.
# This creates a fractal pattern that is self-similar and has a
# fractal dimension (Hausdorff dimension) of log(3)/log(2) = 1.585.


# Generate a random starting point inside the triangle using barycentric coordinates
def random_point_in_triangle(vertices):
    s, t = sorted(np.random.rand(2))
    return s * vertices[0] + (t - s) * vertices[1] + (1 - t) * vertices[2]


# Vertices of the equilateral triangle
vertices = np.array([[0, 0], [1, 0], [0.5, np.sqrt(3)/2]])
point = random_point_in_triangle(vertices)

points = []
for _ in range(10000):
    vertex = vertices[np.random.randint(0, 3)]
    point = (point + vertex) / 2
    points.append(point)

points = np.array(points)
plt.plot(*zip(*vertices, vertices[0]), 'k-')
plt.scatter(points[:, 0], points[:, 1], s=1, color='red')
plt.show()
