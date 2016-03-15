__author__ = 'Artem Bishev'

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from schedule_entities import Job
from scheduler import HybridSchedule


def put_labels_between_ticks(axis, n):
    '''
    Oh gosh.
    There is no any straightforward way to do this simple action in pyplot
    '''
    axis.set_major_locator(ticker.MaxNLocator(nbins=n+1))
    axis.set_minor_locator(ticker.AutoMinorLocator(n=2))

    axis.set_major_formatter(ticker.NullFormatter())
    axis.set_minor_formatter(ticker.ScalarFormatter())

    for tick in axis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment('right')


def plot_windows(schedule):
    jobs_s = sorted(schedule.jobs, key=lambda j: j.start)
    jobs_f = sorted(schedule.jobs, key=lambda j: j.finish)
    leftmost, rightmost = jobs_s[0].start, jobs_f[-1].finish
    total_length = rightmost - leftmost
    leftmost -= total_length * 0.05
    rightmost += total_length * 0.05

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlim(leftmost, rightmost)
    ax.grid(True)
    #ax.plot(...)
    put_labels_between_ticks(ax.yaxis, schedule.partitions_count)
    ax.set_yticklabels(schedule.partitions, minor=True)
    plt.show()


s = HybridSchedule()
s.verbose = 2
jobs = [Job(0, 20, "A", 5),
        Job(2, 20, "B", 5),
        Job(0, 20, "B", 5),
        Job(2, 20, "C", 5)]
s.build(jobs, 5)
print(s.windows)
plot_windows(s)