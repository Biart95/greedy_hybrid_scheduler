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


min_window_size, max_window_size = 10, 100
total_len = 500
min_job_duration, max_job_duration = 1, 40

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

n_runs = 2000

min_h, max_h = [1.01, 3.0]
hardnesses = [7, 10, 14]
n_bins = len(hardnesses) + 1

def pick_bin(hardness):
    # Get bin idx from the hardness value
    global hardnesses
    for i, h in enumerate(hardnesses):
        if hardness < h:
            return i
    return len(hardnesses)


tables = {table_type : np.zeros((len(load_factors), n_bins), dtype=float)
          for table_type in product([False, True], [False, True],
                                    [False, True], [0, 1])}


for (load_idx, load), partition_idx in product(enumerate(load_factors), [0, 1]):
    partitions = partitions_dict[partition_idx]

    print("Load = {}, Partitions = {}\n"
          "".format(load, partitions))

    counts = [0 for _ in range(n_bins)]
    for _ in range(n_runs):
        h = random.uniform(min_h, max_h) # Apriori hardness
        windows = list(generate_windows(min_window_size, max_window_size,
                                        partitions, total_len))
        jobs = list(generate_jobs(windows, h, min_job_duration,
                                  max_job_duration, load))
        hardness = sum(job.length / job.duration
                       for job in jobs) / len(jobs) # Aposteriori hardness
        # choose bin corresponding to the hardness
        h_bin = pick_bin(hardness)
        counts[h_bin] += 1
        # plot_windows(windows, list(partitions.keys()), jobs)

        scores = ['default', 'enhanced']
        for i, j in product([False, True], repeat=2):
            score = 'enhanced' if i else 'default'
            window_score = 'enhanced' if j else 'default'
            recalc_jobs = 1.0 if score == 'enhanced' else 0.0

            s = scheduler.HybridSchedule(score=score,
                                         window_score=window_score,
                                         recalc_jobs=recalc_jobs)
            s.build(jobs, min_window_size)

            q_rate = s.rate()
            q_block = 1.0 if s.exists() else 0.0

            tables[(False, i, j, partition_idx)][load_idx, h_bin] += q_rate
            tables[(True, i, j, partition_idx)][load_idx, h_bin] += q_block

    for i, j, k in product([False, True], repeat=3):
        for h_bin in range(n_bins):
            tables[(i, j, k, partition_idx)][load_idx, h_bin] /= counts[h_bin]


for table_type in product([False, True], [False, True],
                          [False, True], [0, 1]):
    rate_type = "full" if table_type[0] else "avg"
    recalc_jobs = "recalc" if table_type[1] else "norecalc"
    criterion = "enhanced" if table_type[2] else "default"
    table_name = "{}_{}_{}_q{}".format(rate_type, criterion, recalc_jobs,
                                       partitions_counts[table_type[3]])
    x, y = tables[table_type].shape
    result = np.empty((x, y + 1), dtype='|U5')
    result[:, 1:] = tables[table_type]
    result[:, 0] = load_factors
    h = [0] + hardnesses + ["+inf"]
    header = "\t".join([""] + ["[{}, {}]".format(h[i], h[i+1]) for i in range(n_bins)])
    np.savetxt(table_name + ".csv", result, fmt="%s", delimiter="\t", header=header)


#plot_windows(s)
# plot_network(s)