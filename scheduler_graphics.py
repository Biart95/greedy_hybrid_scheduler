__author__ = 'Artem Bishev'

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from schedule_entities import Job, Window
from scheduler import HybridSchedule
import random
from matplotlib.colors import hsv_to_rgb
from itertools import chain
import networkx as nx


def put_labels_between_ticks(axis, n):
    '''
    Oh gosh.
    There is no any straightforward way to do this simple action in pyplot
    '''
    axis.set_minor_locator(ticker.AutoMinorLocator(n=2))

    axis.set_major_formatter(ticker.NullFormatter())
    axis.set_minor_formatter(ticker.ScalarFormatter())

    for tick in axis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment('right')


def filter_indices(pred, seq):
    return [idx for idx, elem in enumerate(seq) if pred(elem)]


def prepare_job_segments(jobs):
    positions = []
    for job in jobs:
        new_pos = random.uniform(0.0, 1.0)
        overlapped_indices = filter_indices(job.have_intersection, jobs)
        overlapped_positions = [positions[idx] for idx in overlapped_indices if idx < len(positions)]
        a = min(chain([1.0], filter(lambda pos: pos >  new_pos, overlapped_positions)))
        b = max(chain([0.0], filter(lambda pos: pos <= new_pos, overlapped_positions)))
        positions.append(0.5 * (a + b))
    return positions


def get_partitions_palette(partitions, saturation=1.0, value=0.5):
    colors = dict()
    for idx, p in enumerate(partitions):
        colors[p] = hsv_to_rgb([idx/len(partitions), saturation, value])
    return colors


def plot_windows(schedule_or_windows, partitions=None, jobs=None, colored=True):
    windows = schedule_or_windows
    if isinstance(schedule_or_windows, HybridSchedule):
        jobs = schedule_or_windows.initial_jobs
        partitions = schedule_or_windows.partitions
        windows = schedule_or_windows.windows
    jobs_s = sorted(jobs, key=lambda j: j.start)
    jobs_f = sorted(jobs, key=lambda j: j.finish)
    leftmost, rightmost = jobs_s[0].start, jobs_f[-1].finish
    total_length = rightmost - leftmost
    leftmost -= total_length * 0.05
    rightmost += total_length * 0.05

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlim(leftmost, rightmost)
    ax.set_ylim(-0.3, len(partitions) + 0.3)
    ax.grid(True)

    colors = get_partitions_palette(partitions)

    for w in windows:
        plt.axvspan(w.start, w.finish, facecolor=colors[w.partition], alpha=0.2)

    for idx, p in enumerate(partitions):
        color = colors[p]
        p_jobs = list(filter(lambda job: job.partition == p, jobs))
        y_coords = prepare_job_segments(p_jobs)
        for y, job in zip(y_coords, p_jobs):
            ax.plot([job.start, job.finish], [idx + y, idx + y],
                    color=color, marker='.', lw=2, ms=10, alpha=0.9)
            label_x = (job.start + job.finish) / 2
            label_y = idx + y + 0.05
            plt.text(label_x, label_y,
                     '{:.1f}/{:.1f}'.format(job.duration, job.length),
                     color=color)

    put_labels_between_ticks(ax.yaxis, len(partitions))
    ax.set_yticks(range(len(partitions) + 1))
    ax.set_yticklabels(partitions, minor=True)
    plt.show()


def plot_network(schedule, colored=True):

    jobs_count = len(schedule.initial_jobs)
    windows_count = len(schedule.windows)
    x_step = 0.5 / (max(windows_count, jobs_count)) ** 0.5

    vertex_positions = dict()
    vertex_labels, edge_labels = dict(), dict()
    vertex_positions["Source"] = (0, 0)
    vertex_positions["Sink"] = (3 * x_step, 0)

    partition_lists = {p: [] for p in schedule.partitions}
    colors = get_partitions_palette(schedule.partitions, saturation=0.35, value=0.8)

    for i, job in enumerate(schedule.initial_jobs):
        y = - (2 * i + 1 - jobs_count) / jobs_count
        vertex_positions[(Job, i)] = (x_step, y)
        vertex_labels[(Job, i)] = str(i)
        partition_lists[job.partition].append((Job, i))

    for i, window in enumerate(schedule.windows):
        y = - (2 * i + 1 - windows_count) / windows_count
        vertex_positions[(Window, i)] = (2 * x_step, y)
        vertex_labels[(Window, i)] = str(i)
        partition_lists[window.partition].append((Window, i))

    for v, w, data in schedule.network.edges(data=True):
        if not (v[0] is Job and w[0] is Window):
            edge_labels[(v, w)] = "{:.1f}".format(float(data["capacity"]))
            try:
                edge_flow = schedule.residual_network[v][w]['flow']
                edge_labels[(v, w)] = "{:.1f}/{}".format(float(edge_flow), edge_labels[(v, w)])
            except AttributeError:
                pass
        else:
            try:
                edge_flow = schedule.residual_network[v][w]['flow']
                edge_labels[(v, w)] = "{:.1f}".format(float(edge_flow))
            except AttributeError:
                pass

    for p in schedule.partitions:
        c = [tuple(colors[p])] * len(partition_lists[p])
        nx.draw_networkx_nodes(schedule.network, vertex_positions,
                               nodelist=partition_lists[p],
                               node_color=c, alpha=1.0)
    nx.draw_networkx_nodes(schedule.network, vertex_positions,
                           nodelist=["Source", "Sink"],
                           node_color=(0.5, 0.5, 0.5))
    nx.draw_networkx_labels(schedule.network, vertex_positions, labels=vertex_labels)
    nx.draw_networkx_edges(schedule.network, vertex_positions, arrows=False)
    nx.draw_networkx_edge_labels(schedule.network, vertex_positions, edge_labels=edge_labels)
    plt.show()


if __name__ == '__main__':
    s = HybridSchedule()
    s.verbose = 2
    jobs = [Job(0, 35, "A", 10),
            Job(2, 20, "B", 5),
            Job(0, 20, "B", 5),
            Job(2, 20, "C", 5),
            Job(18, 28, "D", 6),
            Job(23, 35, "B", 4),
            Job(24, 30, "C", 3)]
    s.build(jobs, 3)
    print(s.windows)
    print(s.exists())
    plot_windows(s)
    plot_network(s)