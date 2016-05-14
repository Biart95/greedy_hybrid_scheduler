__author__ = 'Artem Bishev'


import random
from heapq import merge
from schedule_entities import Job, Window
from scheduler_graphics import plot_windows, plot_network
import scheduler
import matplotlib.pyplot as plt
from pickle import dump
from itertools import product
from collections import defaultdict
import argparse


def generate_windows_one_partition(min_size, max_size, total_len):
    current_len = 0
    while current_len < total_len:
        w = random.uniform(min_size, max_size)
        current_len += w
        yield w


def rate_monotonic_order(rates, items):
    ordered_generators = [[(i / rate, key, item) for i, item in enumerate(items[key])]
                          for key, rate in rates.items()]
    for _, key, item in merge(*ordered_generators):
        yield key, item


def generate_windows(min_size, max_size, partitions, total_len):
    window_sizes, rates = dict(), dict()
    for p, rate in partitions.items():
        window_sizes[p] = list(generate_windows_one_partition(min_size, max_size, rate*total_len))
        rates[p] = len(window_sizes[p])
    time = 0
    for p, size in rate_monotonic_order(rates, window_sizes):
        yield Window(time, time + size, p)
        time += size


def generate_jobs(windows, hardness, min_duration, max_duration, load_factor):
    free_space = [w.length for w in windows]
    total_windows_length = sum(free_space)
    total_jobs_length = 0
    while max(free_space) > min_duration and total_jobs_length < load_factor * total_windows_length:
        duration = random.uniform(min_duration, max_duration)
        matching_indices = [idx for idx, s in enumerate(free_space) if s >= duration]
        if len(matching_indices) == 0:
            continue
        idx = random.choice(matching_indices)
        # h = random.expovariate(1.0 / (hardness - 1.0)) + 1.0
        r = windows[idx].length * (hardness - 1.0)
        a = random.uniform(0.0, 1.0)
        start = windows[idx].start - r * a
        finish = windows[idx].finish + r * (1.0 - a)
        partition = windows[idx].partition
        yield Job(start, finish, partition, duration)
        free_space[idx] -= duration
        total_jobs_length += duration


if __name__ == '__main__':
    jobs_file = open('jobs', 'w')
    windows_file = open('windows', 'w')

    partitions = {'A': 0.1, 'B': 0.1, 'C': 0.2, 'D': 0.3, 'E': 0.3}
    # Generate windows
    windows = list(generate_windows(10, 100, partitions, 500))
    # Save windows to file
    for window in windows:
        print(window.start, window.finish, window.partition, file=windows_file)
    # Generate jobs using the generated list of windows
    hardness, load_factor = 1.1, 0.85
    jobs = list(generate_jobs(windows, hardness, 1, 40, load_factor))
    # Save jobs to file
    for job in jobs:
        print(job.start, job.finish, job.partition, job.duration, file=jobs_file)


