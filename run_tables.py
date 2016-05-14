__author__ = 'Artem Bishev'

from test_gen import *
import random
import numpy as np
from schedule_entities import Job, Window
from scheduler_graphics import plot_windows, plot_network
import scheduler
import matplotlib.pyplot as plt
from itertools import product
from collections import defaultdict


partitions_dict = [{'A': 0.4,
                    'B': 0.6},
                   {'A': 0.1,
                    'B': 0.1,
                    'C': 0.2,
                    'D': 0.3,
                    'E': 0.3}]

partitions_counts = [len(p) for p in partitions_dict]

solutions = dict()

load_factors = [0.9, 0.7, 0.5, 0.3]

hardnesses = [7, 10, 14]

def pick_bin(hardness):
    global hardnesses
    for i, h in enumerate(hardnesses):
        if hardness < h:
            return i
    return len(hardnesses)


tables = {table_type : np.zeros_like(len(load_factors), len(hardnesses) + 1)
          for table_type in product([False, True], [False, True], [0, 1])}


for load in load_factors:
    print("  ========  Load = {}  ========\n".format(load))
    solutions[load] = defaultdict(lambda: [[0, 0] for _ in range(4)])
    counts = [0 for _ in range(4)]
    for _ in range(4000):
        h = random.uniform(1.01, 3.0)
        for
        windows = list(generate_windows(10, 100, partitions, 500))
        jobs = list(generate_jobs(windows, h, 1, 40, load))
        hardness = sum(job.length / job.duration for job in jobs) / len(jobs)
        h_bin = pick_bin(hardness)
        counts[h_bin] += 1
        # plot_windows(windows, list(partitions.keys()), jobs)

        scores = ['default', 'enhanced']
        for score, window_score in product(scores, scores):
            recalc_jobs = 1.0 if score == 'enhanced' else 0.0
            s = scheduler.HybridSchedule(score=score,
                                         window_score=window_score,
                                         recalc_jobs=recalc_jobs)
            s.build(jobs, 10)

            q_rate = s.rate()
            q_block = 1.0 if s.exists() else 0.0

            solutions[load][(score, window_score)][h_bin][0] += q_rate
            solutions[load][(score, window_score)][h_bin][1] += q_block
            print("{} -> {}".format((score, window_score), (q_rate, q_block, hardness)))

        print("")

    for score, window_score in product(scores, scores):
        for h_bin in range(4):
            solutions[load][(score, window_score)][h_bin][0] /= counts[h_bin]
            solutions[load][(score, window_score)][h_bin][1] /= counts[h_bin]

# dump((hardnesses, solutions), "solutions_q2")

for load in [0.9, 0.7, 0.5, 0.3]:
    print("Load = {}".format(load))
    for key, value in solutions[load].items():
        print(key, "->", value)


#plot_windows(s)
# plot_network(s)