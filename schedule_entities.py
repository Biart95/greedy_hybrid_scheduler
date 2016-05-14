#!/usr/bin/env python

__author__ = 'Artem Bishev'

import sys


class IntervalError(ValueError):
    pass


class Interval:
    def __init__(self, start, finish):
        if finish < start:
            raise IntervalError("End of an interval must be >= its start")
        self.start, self.finish = start, finish

    def contains(self, other, eps=1e-3):
        return other.start + eps >= self.start and other.finish - eps <= self.finish

    def intersect(self, other):
        try:
            return Interval(max(self.start, other.start), min(self.finish, other.finish))
        except IntervalError:
            return None

    def have_intersection(self, other, strict=False):
        intersection = self.intersect(other)
        if intersection is None:
            return False
        return (not strict) or intersection.length > 0

    def __eq__(self, other):
        if not isinstance(other, Interval):
            return False
        return self.finish == other.finish and self.start == other.start

    @property
    def length(self):
        return self.finish - self.start

    def __repr__(self):
        return "Interval({}, {})".format(self.start, self.finish)


class Window(Interval):
    def __init__(self, start, finish, partition):
        super().__init__(start, finish)
        self.partition = partition

    def __repr__(self):
        return "Window({}, {}, {})".format(self.start,
                                           self.finish,
                                           self.partition)


class Job(Interval):
    def __init__(self, start, finish, partition, duration):
        super().__init__(start, finish)
        if duration < 0:
            raise ValueError("Job duration must be non-negative")
        if duration > self.length:
            raise ValueError("Job duration must be less or equal than "
                             "the length of its directive interval")
        self.partition = partition
        self.duration = duration

    def __repr__(self):
        return "Job({}, {}, {})".format(self.start, self.finish,
                                        self.partition, self.duration)


def read_input_jobs():
    jobs = []
    for line in sys.stdin:
        job_params = line.strip().split()
        if len(job_params) > 0:
            jobs.append(Job(float(job_params[0]),
                            float(job_params[1]),
                            job_params[2],
                            float(job_params[3])))
    return jobs