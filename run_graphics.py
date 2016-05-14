# -*- coding: utf-8 -*-

__author__ = 'Artem Bishev'

import numpy as np
from test_gen import generate_windows, generate_jobs
from itertools import product
from scheduler import HybridSchedule
import matplotlib.pyplot as plt
import matplotlib
from scheduler_graphics import plot_windows

min_window_size, max_window_size = 10, 100
total_len = 500
min_job_duration, max_job_duration = 1, 40

partitions = {'A': 0.3,
              'B': 0.3,
              'C': 0.4}

load_factor = 0.75

hardnesses = np.linspace(1.0, 2.0, num=20)

n_runs = 100

quality_rate = []
quality_block = []
hardness_arr = []

for h in hardnesses:
    print("h = {}".format(h))
    for _ in range(n_runs):
        windows = list(generate_windows(min_window_size, max_window_size,
                                        partitions, total_len))
        jobs = list(generate_jobs(windows, h, min_job_duration,
                                  max_job_duration, load_factor))

        hardness = sum(job.length / job.duration
                       for job in jobs) / len(jobs) # Aposteriori hardness
        q_rate = []
        q_block = []

        scores = ['default', 'enhanced']
        for score, window_score in product(scores, repeat=2):
            recalc_jobs = 1.0 if score == 'enhanced' else 0.0
            s = HybridSchedule(score, window_score, recalc_jobs)
            s.build(jobs, min_window_size)
            q_rate.append(s.rate())
            q_block.append(1.0 if s.exists() else 0.0)

        quality_block.append(q_block)
        quality_rate.append(q_rate)
        hardness_arr.append(hardness)

quality_rate = np.array(quality_rate)
quality_block = np.array(quality_block)
hardness_arr = np.array(hardness_arr)

hist, bins = np.histogram(hardness_arr, bins=20)
x = [0.5 * (bins[i + 1] + bins[i])
     for i, _ in enumerate(hist[:-5])]
y = []
for i, count in enumerate(hist[:-5]):
    mask = (bins[i] <= hardness_arr) & (hardness_arr < bins[i + 1])
    y.append(np.mean(quality_block[mask], axis=0))

y = np.array(y)
matplotlib.rc('font', family="Courier New")
for i in range(y.shape[1]):
    plt.plot(x, y[:, i])
    plt.xlabel("Жёсткость директивных интервалов")
    plt.ylabel("Доля полностью построенных расписаний")
plt.show()


windows = list(generate_windows(min_window_size, max_window_size,
                                partitions, 700))
jobs = list(generate_jobs(windows, 1.05, min_job_duration,
                          max_job_duration, 0.85))

plot_windows(windows, partitions=partitions, jobs=jobs)

s = HybridSchedule('enhanced', 'enhanced', recalc_jobs=1.0)
s.build(jobs, min_window_size)

plot_windows(s)


