#! /usr/bin/env python3

import math
import sys
import random

import euclidean_graph

MAX_SEED = 10000000


def road(f, t, length, plow_cost):
    length = int(math.ceil(length / 10.0))
    print(f"  (road_unknown {f} {t})")
    print("  (= (road-length %s %s) %d)" % (f, t, length))
    print("  (= (plow-cost %s %s) %d)" % (f, t, plow_cost))


def symmetric_road(f, t, length, plow_cost):
    road(f, t, length, plow_cost)
    road(t, f, length, plow_cost)


def shortest_route(ca, cb, ox, oy):
    # connect the two cities
    min_connect_distance = -1.0
    for v in ca.vertices:
        for u in cb.vertices:
            if (
                v.distance(euclidean_graph.Point(u.name, u.x + ox, u.y + oy))
                < min_connect_distance
                or min_connect_distance == -1.0
            ):
                min_tuple = (v, u)
                min_connect_distance = v.distance(
                    euclidean_graph.Point(u.name, u.x + 2 * size, u.y)
                )

    return min_tuple, min_connect_distance


if len(sys.argv) != 10:
    raise SystemExit(
        "Usage: <cost-mode:DISTANCE|SIZE|SQUARE_SIZE> <cities> <nodes> <size^(1/2)> <degree> <mindistance> <nr-trucks> <nr-packages> <seed>"
    )

cost_mode = sys.argv[1]

n_cities = int(sys.argv[2])
nodes = int(sys.argv[3])
size = int(sys.argv[4])
degree = float(sys.argv[5])
epsilon = float(sys.argv[6])
trucks = int(sys.argv[7])
packages = int(sys.argv[8])
seed = float(sys.argv[9])

if cost_mode.lower() == "distance":
    plow_cost = epsilon
elif cost_mode.lower() == "size":
    plow_cost = size
elif cost_mode.lower() == "square_size":
    plow_cost = size * size
else:
    raise SystemExit(
        "Usage: <cost-mode:DISTANCE|SIZE|SQUARE_SIZE> <cities> <nodes> <size^(1/2)> <degree> <mindistance> <nr-trucks> <nr-packages> <seed>"
    )

max_capacity = 4  # maximum number of packages in one truck
assert max_capacity > 2

if not seed:
    seed = random.randrange(MAX_SEED) + 1
random.seed(seed)

#         deg * width * height
# ratio = ---------------------------
#         nodes * pi * Connect^2
connect_distance = math.sqrt((degree * size * size) / (nodes * math.pi * 0.694))

cities = [
    euclidean_graph.generate_connected_safe(
        nodes, size, size, connect_distance, epsilon
    )
    for i in range(n_cities)
]

city_connections = {
    (i,j): shortest_route(cities[i], cities[j], size, 2 * size)
    for i in range(n_cities - 1)
    for j in range(i + 1, n_cities)
}

id = (
    "sequential-%dcities-%dnodes-%dsize-%ddegree-%dmindistance-%dtrucks-%dpackages-%dseed"
    % (n_cities, nodes, size, degree, epsilon, trucks, packages, seed)
)

print("; Canadian Transport %s" % id)
print()

print("(define (problem canadian-transport-%s)" % id)
print(" (:domain canadian-transport)")
print(" (:objects")

for j in range(n_cities):
    for i in range(nodes):
        print("  city-%d-loc-%d - location" % (j + 1, i + 1))
for i in range(trucks):
    print("  truck-%d - vehicle" % (i + 1))

for i in range(packages):
    print("  package-%d - package" % (i + 1))

for i in range(max_capacity + 1):
    print("  capacity-%d - capacity-number" % i)

print(" )")
print(" (:init")

print("  (= (total-cost) 0)")
print("  (plow)")


for i in range(max_capacity):
    print("  (capacity-predecessor capacity-%d capacity-%d)" % (i, i + 1))

for j in range(n_cities):
    for u, v in cities[j].edges:
        print("  ; %d,%d -> %d,%d" % (u.x, u.y, v.x, v.y))

        dist = u.round_distance(v)
        road(
            "city-%d-" % (j + 1) + u.name,
            "city-%d-" % (j + 1) + v.name,
            dist,
            plow_cost,
        )

for i,j in city_connections:
    connect_ac, dist_ac = city_connections[(i, j)]
    symmetric_road(
        "city-%d-" % (i + 1) + connect_ac[0].name,
        "city-%d-" % (j + 1) + connect_ac[1].name,
        dist_ac,
        plow_cost,
    )

truck_loc = []
for i in range(trucks):
    c,l = random.randint(1, n_cities), random.choice(cities[0].vertices).name
    truck_loc.append((c, l))
    print(
        "  (at truck-%d city-%d-%s)"
        % (i + 1, c, l)
    )
    capacity = random.randint(2, 4)
    print("  (capacity truck-%d capacity-%d)" % (i + 1, capacity))

package_loc = {}
for i in range(packages):
    c,l = random.randint(1, n_cities), random.choice(cities[0].vertices).name
    package_loc["package-%d" % (i + 1)] = (
        c,
        l
    )
    print(
        "  (at package-%d city-%d-%s)"
        % (
            i + 1,
            package_loc["package-%d" % (i + 1)][0],
            package_loc["package-%d" % (i + 1)][1],
        )
    )


print(" )")
print(" (:goal (and")

for i in range(packages):
    rc = random.randint(1, n_cities)
    rl = random.choice(cities[rc - 1].vertices).name
    while (
        rc == package_loc["package-%d" % (i + 1)][0]
        and rl == package_loc["package-%d" % (i + 1)][1]
    ):
        rc = random.randint(1, n_cities)
        rl = random.choice(cities[rc - 1].vertices).name
    print("  (at package-%d city-%d-%s)" % (i + 1, rc, rl))

print(" ))")

print(" (:metric minimize (total-cost))")

print(")")
