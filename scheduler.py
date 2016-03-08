__author__ = 'Artyom Bishev'

from copy import deepcopy
from itertools import chain

class Interval:
    def __init__(self, start, finish):
        self.start, self.finish = start, finish

    def contains(self, other):
        return other.start >= self.start and other.finish <= self.finish

    @property
    def length(self):
        return self.finish - self.start


class Window(Interval):
    def __init__(self, start, finish, partition):
        super().__init__(start, finish)
        self.partition = partition

    def __str__(self):
        return "Window({}, {}, {})".format(self.start,
                                           self.finish,
                                           self.partition)


class Job(Interval):
    def __init__(self, start, finish, partition, duration):
        super().__init__(start, finish)
        self.partition = partition
        self.duration = duration

    def __str__(self):
        return "Job({}, {}, {})".format(self.start, self.finish,
                                        self.partition, self.duration)


def default_score(interval, job, time):
    ''' Get value that describes the fitness of this job to the given interval
    '''
    part = interval.length / job.length
    hardness = job.duration / (job.finish - job.start)
    return part * hardness

def enhanced_score(interval, job, time):
    ''' This criterion explicitly includes the penalty
        for a delay between the end of previous window
        and the beginning of current window
    '''
    part = interval.length / job.length
    hardness = job.duration / (job.finish - time)
    return part * hardness

def get_window_score(score, window, job, time):
    ''' Get value that describes the fitness of this job to the given window
    '''
    if window.contains(job) and window.partition == job.partition:
        return score(window, job, time)
    return 0.0

def get_enhanced_window_score(score, window, job, time):
    ''' This function includes the penalty for the window
        overlapping the parts of jobs that cannot be scheduled in it
    '''
    if window.contains(job) and window.partition == job.partition:
        return score(window, job, time)
    if window.start < job.start < window.finish:
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

class HybridSchedule:
    def __init__(self, score='enhanced', window_score='enhanced'):
        if isinstance(score, str):
            score = score_criteria[score]
        if isinstance(window_score, str):
            window_score = window_score_criteria[window_score]
        self.score = score
        self.window_score = lambda w, j, t: window_score(score, w, j, t)
        self.verbose = 0

    def build(self, jobs, min_window_size):
        self.jobs = deepcopy(jobs)
        self.min_window_size = min_window_size
        self.partitions_count = max(job.partition for job in jobs) + 1
        self.__verbose_print("Building the schedule with d={}".format(self.min_window_size))
        self.__verbose_print("Number of partitions is {}".format(self.partitions_count))
        self.__verbose_print("Number of jobs is {}".format(len(self.jobs)))
        self.windows = list(self.__find_windows())
        self.__build_network()
        self.__find_schedule()

    def __verbose_print(self, *msg):
        if self.verbose > 0:
            print(*msg)

    def __getattr__(self, attr):
        if attr in ["jobs", "windows",  "network", "jobs_distribution", "partitions_count"]:
            raise AttributeError("You must run the build method before trying to access the resulting data")
        else:
            raise AttributeError("HybridSchedule instance has no attribute '{}'".format(attr))

    def __find_windows(self):
        ''' Find the set of windows using a greedy strategy
        '''
        # Get all moments of time when some job's directive interval is starting or is finishing
        # We will call all intervals between these moments as 'sub-intervals'
        timestamps = sorted(set(([job.start for job in self.jobs] +
                                 [job.finish for job in self.jobs])))
        self.__verbose_print("\n ==================================== ")
        self.__verbose_print("== Searching for the set of windows ==")
        self.__verbose_print(" ==================================== \n")
        self.__verbose_print("Timestamps:", timestamps)

        time, count = timestamps[0], 0
        while len(timestamps) > 0 and time + self.min_window_size <= timestamps[-1]:
            # Perform a step of the greedy algorithm
            self.__verbose_print("\n====| Step #{}. Time = {} |====\n".format(count, time))
            # Get all candidates for the next window
            possible_windows = list(self.__possible_windows(time))
            self.__verbose_print("Possible windows:", possible_windows)
            if len(possible_windows) > 1:
                # If there are some, chose the best of them according to
                # the given greedy criterion. The partition of the new window
                # is also chosen here.
                window = self.__find_best_window(possible_windows, time)
                time = window.finish
                yield window
            else:
                # In case there is no appropriate windows,
                # (i.e. we have a very long sub-interval of length >> min_window_size)
                # split the next sub-interval by new windows correspondingly to their weights.
                # The weights can be also determined as the values of greedy criterion
                finish = min(filter(timestamps, lambda t: t > time)) # end of the sub-interval
                for window in self.__split_subinterval_by_windows(time, finish):
                    yield window
                time = finish
            count += 1

    def __find_best_window(self, possible_windows, time):
        ''' Find the best window from the given set of windows using a greedy criterion
        :return: best fitted window
        '''
        best_score, best_window = None, None
        for window_start, window_finish in possible_windows:
            for p in range(self.partitions_count):
                window = Window(window_start, window_finish, p)
                score = self.__calculate_greedy_func(window, time)
                if best_score is None or score > best_score:
                    best_score, best_window = score, window
        self.__verbose_print("Best window is {} with score {}".format(best_window, best_score))
        return best_window

    def __calculate_greedy_func(self, window, time):
        return sum(self.window_score(window, job, time) for job in self.jobs)

    def __possible_windows(self, time):
        ''' Generate the best fitting intervals for the next window,
            assuming that the previous scheduled window ended in the specified time

            :param time - the moment of time when the last window ended
            :returns yields appropriate intervals (start, end) of the new window
        '''
        max_start_time = time + self.min_window_size
        max_finish_time = max_start_time + self.min_window_size
        # Construct the list of possible start times of the window
        possible_start_time = set(filter(lambda t: time <= t < max_start_time,
                                         [job.start for job in self.jobs]))
        if len(possible_start_time) == 0 or time not in possible_start_time:
            possible_start_time.add(time)
        self.__verbose_print("Possible start:", possible_start_time)
        # For each possible start of the window:
        for start in possible_start_time:
            # Construct the list of possible finish times of the window
            min_finish_time = start + self.min_window_size
            timestamps = chain([job.start for job in self.jobs],
                               [job.finish for job in self.jobs])
            possible_finish_time = set(filter(lambda t: min_finish_time <= t < max_finish_time,
                                              timestamps))
            if len(possible_finish_time) == 0 or min_finish_time not in possible_finish_time:
                possible_finish_time.add(min_finish_time)
            # For each possible finish of the window:
            for finish in possible_finish_time:
                yield (start, finish)

    def __split_subinterval_by_windows(self, start, finish):
        ''' Fill the interval between 'start' and 'finish'
            by windows of different partitions
            picking their sizes according to a greedy criteria
        '''
        self.__verbose_print("Subinterval ({}, {}) is too long.".format(start, finish))
        def filter_jobs(p):
            return filter(lambda job: job.start <= start and
                                      job.finish >= finish and
                                      job.partition == p, self.jobs)
        jobs = [filter_jobs(p) for p in range(self.partitions_count)]
        durations = [sum(job.duration for job in jobs[p]) for p in range(self.partitions_count)]
        weights = [sum(self.score(Interval(start, finish), job, start) for job in jobs[p])
                   for p in range(self.partitions_count)]
        weights = [w / sum(weights) for w in weights]
        self.__verbose_print("Weights are", weights)
        durations = [min(w * (finish - start), d) for w, d in zip(weights, durations)]
        self.__verbose_print("Durations are", durations)
        partitions_order = sorted(range(self.partitions_count), key=lambda p: durations[p])
        for p in partitions_order:
            if start + durations[p] > finish:
                return
            yield Window(start, start + durations[p], p)
            start += durations[p]

    def __build_network(self):
        pass

    def __find_schedule(self):
        pass


def main():
    s = HybridSchedule()
    s.verbose = 1
    jobs = [Job(0, 20, 0, 5),
            Job(0, 32, 0, 6),
            Job(12, 51, 1, 10),
            Job(15, 47, 1, 20),
            Job(21, 62, 0, 20),
            Job(33, 50, 0, 8),
            Job(51, 100, 1, 25),
            Job(64, 98, 0, 4),
            Job(79, 88, 0, 7),
            Job(77, 110, 1, 11)]
    s.build(jobs, 28)

if __name__ == '__main__':
    main()
