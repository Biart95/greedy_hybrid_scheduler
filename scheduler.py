#!/usr/bin/env python

__author__ = 'Artem Bishev'

from copy import deepcopy
from itertools import chain
from schedule_entities import Job, Interval, Window


def default_score(interval, job, time):
    '''
    Get value that describes the fitness of this job to the given interval
    '''
    part = interval.length / job.length
    hardness = job.duration / job.length
    return part * hardness


def enhanced_score(interval, job, time):
    '''
    This criterion explicitly includes the penalty
    for a delay between the end of previous window
    and the beginning of current window
    '''
    part = interval.length / float(job.finish - time)
    hardness = job.duration / float(job.finish - time)
    return part * hardness


def get_window_score(score, window, job, time):
    '''
    Get value that describes the fitness of this job to the given window
    '''
    if job.contains(window) and window.partition == job.partition:
        return score(window, job, time)
    return 0.0


def get_enhanced_window_score(score, window, job, time):
    '''
    This function includes the penalty for the window in case it
    overlaps some parts of jobs which cannot be scheduled in this window
    '''
    if job.contains(window) and window.partition == job.partition:
        print ("+", score(window, job, time), end=" ")
        return score(window, job, time)
    elif job.contains(window):
        print ("-", score(Interval(time, window.finish), job, time), end=" ")
        return -score(Interval(time, window.finish), job, time)
    elif window.start < job.start < window.finish:
        print ("-", score(Interval(job.start, window.finish), job, time), end=" ")
        return -score(Interval(job.start, window.finish), job, time)
    return 0.0


score_criteria = {
    'default': default_score,
    'enhanced': enhanced_score
}

window_score_criteria = {
    'default': get_window_score,
    'enhanced': get_enhanced_window_score
}


def get_acceptable_following_windows(time, jobs, min_window_size, verbose=False):
    '''
    Generate the best fitting intervals for the next window,
    assuming that the previous scheduled window ended in the specified time

    :param time - the moment of time when the last window ended
    :returns yields appropriate intervals (start, end) of the new window
    '''
    max_start_time = time + min_window_size
    # Construct the list of possible start times of the window
    possible_start_time = set(filter(lambda t: time <= t < max_start_time,
                                     [job.start for job in jobs]))
    if len(possible_start_time) == 0 or time not in possible_start_time:
        possible_start_time.add(time)
    if verbose: print("Possible start:", possible_start_time)
    # For each possible start of the window:
    for start in possible_start_time:
        # Construct the list of possible finish times of the window
        max_finish_time = start + 2*min_window_size
        min_finish_time = start + min_window_size
        timestamps = chain([job.start for job in jobs],
                           [job.finish for job in jobs])
        possible_finish_time = set(filter(lambda t: min_finish_time <= t < max_finish_time,
                                          timestamps))
        if len(possible_finish_time) == 0 or min_finish_time not in possible_finish_time:
            possible_finish_time.add(min_finish_time)
        # For each possible finish of the window:
        for finish in possible_finish_time:
            yield (start, finish)


def distribute_intervals(interval, distribution, max_sizes, min_sizes):
    '''
    Fill the interval by sub-intervals with lengths laying in given bounds
    picking their sizes close to the given distribution
    '''
    assert(isinstance(interval, Interval))
    total = sum(distribution)
    # Estimate lengths of sub-intervals
    durations = [min(s, d / total * interval.length)
                 for s, d in zip(max_sizes, distribution)]
    # Sort them. Longer sub-intervals go first
    order = sorted(range(len(durations)), key=lambda p: -durations[p])
    # Fill the interval iteratively by sub-intervals with calculated lengths
    # Until sub-intervals don't fit into the rest of the interval's space
    result = [None for _ in durations]
    start = interval.start
    for p in order:
        length = max(durations[p], min_sizes[p])
        if start + length > interval.finish:
            break
        start += length
    # Expand the intervals so they occupy as much space as possible
    total_delta = interval.finish - start
    start = interval.start
    for p in order:
        length = max(durations[p], min_sizes[p])
        delta = min(total_delta, max_sizes[p] - length)
        length += delta
        total_delta -= delta
        if start + length > interval.finish:
            break
        result[p] = Interval(start, start + length)
        start += length
    # Return the calculated  sub-intervals
    return result


class HybridSchedule:

    def __init__(self, score='enhanced', window_score='enhanced', recalc_jobs=1.0):
        if isinstance(score, str):
            score = score_criteria[score]
        if isinstance(window_score, str):
            window_score = window_score_criteria[window_score]
        self.score = score
        self.window_score = lambda w, j, t: window_score(score, w, j, t)
        self.verbose = 0
        self.recalc_jobs = recalc_jobs


    def build(self, jobs, min_window_size):

        # Initialize the members
        self.jobs = deepcopy(jobs)
        self.min_window_size = min_window_size
        self.partitions = list(set(job.partition for job in jobs))
        self.partitions_count = len(self.partitions)

        # Verbose output
        self.__verbose_print("Building the schedule with d={}".format(self.min_window_size))
        self.__verbose_print("Number of partitions is {}".format(self.partitions_count))
        self.__verbose_print("Number of jobs is {}".format(len(self.jobs)))

        # Find the windows using a greedy strategy
        self.windows = list(self.__find_windows())

        # Build the network to solve the rest of our task
        self.__build_network()

        # Find max flow of the network and find the final solution
        self.__find_schedule()


    def __verbose_print(self, *args, **kwargs):
        if self.verbose > 0:
            print(*args, **kwargs)


    def __getattr__(self, attr):
        if attr in ["jobs", "windows",  "network", "jobs_distribution", "partitions_count"]:
            raise AttributeError("You must run the build method before trying to access the resulting data")
        else:
            raise AttributeError("HybridSchedule instance has no attribute '{}'".format(attr))


    def __find_windows(self):
        '''
        Find the set of windows using a greedy strategy
        '''

        # Get all moments of time when some job's directive interval is starting or is finishing
        # We will further call all intervals between these moments as 'sub-intervals'
        timestamps = sorted(set(([job.start for job in self.jobs] +
                                 [job.finish for job in self.jobs])))

        self.__verbose_print("\n ==================================== ")
        self.__verbose_print("== Searching for the set of windows ==")
        self.__verbose_print(" ==================================== \n")
        self.__verbose_print("Timestamps:", timestamps)

        # Perform steps of the greedy algorithm
        time, count = timestamps[0], 0
        while len(timestamps) > 0 and time + self.min_window_size <= timestamps[-1]:
            self.__verbose_print("\n====| Step #{}. Time = {} |====\n".format(count, time))
            # Get all candidates for the next window
            possible_windows = list(get_acceptable_following_windows(time, self.jobs,
                                                                     self.min_window_size,
                                                                     self.verbose > 0))
            self.__verbose_print("Possible windows:", possible_windows)
            if len(possible_windows) > 1:
                # If there are some, chose the best of them according to
                # the given greedy criterion. The partition of the new window
                # is also chosen here.
                window = self.__find_best_window(possible_windows, time)
                self.__recalc_jobs(window, time)
                time = window.finish
                yield window
            else:
                # In case there is no appropriate windows,
                # (i.e. we have a very long sub-interval of length >> min_window_size)
                # split the next sub-interval by new windows correspondingly to their weights.
                # The weights can be also determined as the values of greedy criterion
                finish = min(filter(lambda t: t > time, timestamps))  # end of the sub-interval
                for window in self.__split_subinterval_by_windows(Interval(time, finish)):
                    self.__recalc_jobs(window, time)
                    yield window
                time = finish
            count += 1


    def __recalc_jobs(self, window, time):
        '''
        Procedure that recalculates durations of the jobs as if some of them are
        scheduled into the given window. New durations will be equal to the old ones
        minus estimated time of their execution inside the window
        '''

        scores = [max(0.0, self.window_score(window, job, time)) for job in self.jobs]
        total = sum(scores)
        deltas = [score / total * window.length for score in scores]
        for job, delta in zip(self.jobs, deltas):
            job.duration = max(0, job.duration - self.recalc_jobs * delta)


    def __find_best_window(self, intervals, time):
        '''
        Find the best window from the given set of intervals using a greedy criterion
        :return: best fitted window
        '''
        best_score, best_window = None, None
        for window_start, window_finish in intervals:
            for p in self.partitions:
                window = Window(window_start, window_finish, p)
                score = self.__calculate_greedy_func(window, time)
                if self.verbose > 1:
                    print(window, "score = {}".format(score))
                if best_score is None or score > best_score:
                    best_score, best_window = score, window
        self.__verbose_print("Best window is {} with score {}".format(best_window, best_score))
        return best_window


    def __calculate_greedy_func(self, window, time):
        result = sum(self.window_score(window, job, time) for job in self.jobs)
        print("")
        return result


    def __split_subinterval_by_windows(self, interval):
        '''
        Fill the interval by windows of different partitions
        picking their sizes according to a greedy criteria
        '''

        self.__verbose_print("Subinterval ({}, {}) is too long.".format(interval.start,
                                                                        interval.finish))

        # Define filter that lefts only jobs of given partition p which contain the interval
        def filter_jobs(p):
            return filter(lambda job: job.contains(interval) and
                                      job.partition == self.partitions[p], self.jobs)

        # Get a list of acceptable jobs for each partition
        jobs = [list(filter_jobs(p)) for p in range(self.partitions_count)]
        # Get total durations of jobs which belong to partition p
        # (for each partition)
        durations = [sum(job.duration for job in jobs[p])
                     for p in range(self.partitions_count)]
        # Get weights (based on greedy criteria) of jobs which belong to partition p
        # (for each partition)
        weights = [sum(self.score(interval, job, interval.start) for job in jobs[p])
                   for p in range(self.partitions_count)]

        # distribute windows of each partition along the interval
        min_sizes = [self.min_window_size for _ in self.partitions]
        window_intervals = distribute_intervals(interval, weights, durations, min_sizes)
        for p, i in enumerate(window_intervals):
            if i is not None:
                yield Window(i.start, i.finish, self.partitions[p])


    def __build_network(self):
        pass


    def __find_schedule(self):
        pass


def main():
    s = HybridSchedule()
    s.verbose = 2
    jobs = [Job(0, 20, "A", 5),
            Job(2, 20, "B", 5),
            Job(0, 20, "B", 5),
            Job(2, 20, "C", 5)]
    s.build(jobs, 5)
    print(s.windows)

if __name__ == '__main__':
    main()
