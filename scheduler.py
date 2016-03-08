__author__ = 'Artyom Bishev'

from copy import deepcopy

def filter_sorted_list(sorted_list, val, less=True, equal=True):
    i = 0
    for value in sorted_list:
        if value > val or (less == (not equal)) and value >= val:
            break
        i += 1
    return sorted_list[:i] if less else sorted_list[i:]

def remove_repeats_sorted(sorted_seq):
    last_value = None
    for value in sorted_seq:
        if value != last_value:
            last_value = value
            yield value

def filter_sorted_list_interval(sorted_list, l, r, equal_l=True, equal_r=False):
    return filter_sorted_list(filter_sorted_list(sorted_list, l, False, equal_l),
                              r, True, equal_r)



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
    ''' Get value that describes the fitness of this job to the given interval '''
    part = interval.length / job.length
    hardness = job.duration / (job.finish - time)
    return part * hardness


def get_window_score(score, window, job, time):
    if window.contains(job) and window.partition == job.partition:
        return score(window, job, time)
    return 0.0


def get_corrected_window_score(score, window, job, time):
    if window.contains(job) and window.partition == job.partition:
        return score(window, job, time)
    if window.start < job.start < window.finish:
        return -score(Interval(job.start, window.finish), job, time)
    return 0.0


class HybridSchedule:
    def __init__(self):
        self.score = lambda w, j, t: get_corrected_window_score(default_score, w, j, t)
        self.verbose = 0

    def build(self, jobs, min_window_size):
        self.jobs = deepcopy(jobs)
        self.min_window_size = min_window_size
        self.partitions_count = max(job.partition for job in jobs) + 1
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
        ''' Find the set of windows using a greedy strategy '''
        timestamps = sorted(set(([job.start for job in self.jobs] +
                                 [job.finish for job in self.jobs])))
        start_timestamps = sorted(set(job.start for job in self.jobs))

        self.__verbose_print("Timestamps:", timestamps)
        self.__verbose_print("Start timestamps:", start_timestamps)

        time, count = timestamps[0], 0
        while len(timestamps) > 0 and time + self.min_window_size <= timestamps[-1]:
            self.__verbose_print("\n====| Step #{}. Time = {} |====\n".format(count, time))
            possible_windows = list(self.__possible_windows(time, timestamps, start_timestamps))
            self.__verbose_print("Possible windows:", possible_windows)
            if len(possible_windows) > 1:
                window = self.__find_best_window(possible_windows, time)
                time = window.finish
                yield window
            else:
                for window in self.__split_subinterval_by_windows(time, timestamps[0]):
                    time = window.finish
                    yield window
            count += 1
            timestamps = filter_sorted_list(timestamps, time, False)

    def __find_best_window(self, possible_windows, time):
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
        return sum(self.score(window, job, time) for job in self.jobs)

    def __possible_windows(self, time, timestamps, start_timestamps):
        max_start_time = time + self.min_window_size
        max_finish_time = max_start_time + self.min_window_size
        # Construct the list of possible start times of the window
        possible_start_time = filter_sorted_list_interval(start_timestamps, time, max_start_time)
        if len(possible_start_time) == 0 or possible_start_time[0] != time:
            possible_start_time = [time] + possible_start_time
        self.__verbose_print("Possible start:", possible_start_time)
        # For each possible start of the window:
        for start in possible_start_time:
            # Construct the list of possible finish times of the window
            possible_finish_time = filter_sorted_list_interval(
                timestamps, start + self.min_window_size, max_finish_time
            )
            if len(possible_finish_time) == 0 or possible_finish_time[0] != start + self.min_window_size:
                possible_finish_time = [start + self.min_window_size] + possible_finish_time
            # For each possible finish of the window:
            for finish in possible_finish_time:
                yield (start, finish)

    def __split_subinterval_by_windows(self, start, finish):
        jobs = filter(lambda job: job.start <= start and job.finish >= finish, self.jobs)
        #objectives = map(jobs


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
