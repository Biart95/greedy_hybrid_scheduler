#!/usr/bin/env python

__author__ = 'Artem Bishev'

from schedule_entities import IntervalError, Job, Window, Interval
from scheduler import get_acceptable_following_windows, distribute_intervals
import unittest


class BasicEntitiesTests(unittest.TestCase):
    '''
    Test capabilities of basic entities related to schedules
    '''
    def test_interval_exceptions(self):
        with self.assertRaises(IntervalError):
            a = Interval(2, 1)
        with self.assertRaises(IntervalError):
            b = Job(3, 1, 1, 1)
        with self.assertRaises(IntervalError):
            c = Window(3, 1, 1)
        d = Window(1, 1, 1)
        e = Window(-3, -2, 1)

    def test_job_exceptions(self):
        with self.assertRaises(ValueError):
            a = Job(1, 3, 1, 3)
        with self.assertRaises(ValueError):
            b = Job(1, 3, 1, -1)
        c = Job(100, 200, 1, 100)
        d = Job(-3, -1, 1, 0)

    def test_contains(self):
        ad = Interval(0, 3)
        ab = Interval(0, 1)
        ac = Interval(0, 2)
        bd = Job(1, 3, 1, 1)
        bc = Window(1, 2, 2)
        z = Interval(1.5, 1.5)
        for x in [ad, ab, ac, bd, bc, z]:
            self.assertTrue(ad.contains(x))
            self.assertTrue(x.contains(x))
        for x in [ad, ac, bd, bc]:
            self.assertTrue(x.contains(z))
            self.assertFalse(z.contains(x))
        self.assertTrue(bd.contains(bc))
        self.assertTrue(ac.contains(bc))
        self.assertTrue(ac.contains(ab))
        self.assertFalse(ab.contains(bc))
        self.assertFalse(bd.contains(ab))
        self.assertFalse(ab.contains(z))

    def test_eq(self):
        self.assertEqual(Interval(0, 3), Job(0, 3, 1, 1))
        self.assertNotEqual(Window(0, 3, 1), Window(1, 3, 1))


class FindWindowsTests(unittest.TestCase):
    '''
    Test get_acceptable_following_windows function
    '''
    def setUp(self):
        self.jobs = [Job(0,  10, 0, 5),
                     Job(5,  15, 0, 5),
                     Job(10, 20, 1, 5),
                     Job(20, 23, 2, 2),
                     Job(25, 30, 2, 4),
                     Job(40, 50, 1, 2),
                     Job(40, 50, 2, 2),
                     Job(40, 60, 1, 5),
                     Job(80, 100, 0, 10),
                     Job(90, 100, 0, 8)]
        # timestamps:
        #     10----20                 40------60
        # 0---10    20---23  25---30   40---50     80-------100
        #   5----15                    40---50         90---100

    def test_simple_case(self):
        windows_list = list(get_acceptable_following_windows(19, self.jobs, 5))
        self.assertEqual(len(windows_list), 3)
        windows = set(windows_list)
        self.assertEqual(len(windows), 3)
        self.assertIn((19, 24), windows)
        self.assertIn((19, 25), windows)
        self.assertIn((20, 25), windows)

    def test_min_window_size(self):
        min_window_size = 24
        windows_list = list(get_acceptable_following_windows(2, self.jobs, min_window_size))
        for window in windows_list:
            self.assertGreaterEqual(window[1] - window[0], min_window_size)
            self.assertLess(window[1] - window[0], 2*min_window_size)

    def test_borders_0(self):
        windows_list = list(get_acceptable_following_windows(0, self.jobs, 5))
        self.assertEqual(len(windows_list), 1)
        windows = set(windows_list)
        self.assertEqual(len(windows), 1)
        self.assertIn((0, 5), windows)

    def test_borders_1(self):
        windows_list = list(get_acceptable_following_windows(0, self.jobs, 6))
        self.assertEqual(len(windows_list), 4)
        windows = set(windows_list)
        self.assertEqual(len(windows), 4)
        self.assertIn((0, 6), windows)
        self.assertIn((0, 10), windows)
        self.assertIn((5, 11), windows)
        self.assertIn((5, 15), windows)

    def test_borders_2(self):
        windows_list = list(get_acceptable_following_windows(0, self.jobs, 10))
        self.assertEqual(len(windows_list), 5)
        windows = set(windows_list)
        self.assertEqual(len(windows), 5)
        self.assertIn((0, 10), windows)
        self.assertIn((0, 15), windows)
        self.assertIn((5, 15), windows)
        self.assertIn((5, 20), windows)
        self.assertIn((5, 23), windows)

    def test_borders_3(self):
        windows_list = list(get_acceptable_following_windows(35, self.jobs, 10))
        self.assertEqual(len(windows_list), 3)
        windows = set(windows_list)
        self.assertEqual(len(windows), 3)
        self.assertIn((35, 45), windows)
        self.assertIn((35, 50), windows)
        self.assertIn((40, 50), windows)

    def test_borders_4(self):
        windows_list = list(get_acceptable_following_windows(35, self.jobs, 8))
        self.assertEqual(len(windows_list), 4)
        windows = set(windows_list)
        self.assertEqual(len(windows), 4)
        self.assertIn((35, 43), windows)
        self.assertIn((35, 50), windows)
        self.assertIn((40, 48), windows)
        self.assertIn((40, 50), windows)

    def test_borders_5(self):
        windows_list = list(get_acceptable_following_windows(29, self.jobs, 10))
        self.assertEqual(len(windows_list), 2)
        windows = set(windows_list)
        self.assertEqual(len(windows), 2)
        self.assertIn((29, 39), windows)
        self.assertIn((29, 40), windows)

    def test_no_timestamps(self):
        windows_list = list(get_acceptable_following_windows(31, self.jobs, 2))
        self.assertEqual(len(windows_list), 1)
        windows = set(windows_list)
        self.assertEqual(len(windows), 1)
        self.assertIn((31, 33), windows)

    def test_one_window(self):
        windows_list = list(get_acceptable_following_windows(25, self.jobs, 5))
        self.assertEqual(len(windows_list), 1)
        windows = set(windows_list)
        self.assertEqual(len(windows), 1)
        self.assertIn((25, 30), windows)


class DistributeIntervalsTest(unittest.TestCase):
    def test_full_capacity(self):
        interval = Interval(0, 10)
        max_sizes = [4, 3, 2, 2]
        min_sizes = [2, 2, 2, 2]
        weights = [3.0, 4.0, 2.0, 1.0]
        self.assertNotIn(None, distribute_intervals(interval, weights,
                                                    max_sizes, min_sizes))

    def test_common(self):
        interval = Interval(-7, 7)
        max_sizes = [10, 8, 7, 5, 4]
        min_sizes = [5, 5, 4, 4, 3]
        weights = [1.5, 4.0, 5.0, 1.5, 2.0]
        intervals = distribute_intervals(interval, weights,
                                         max_sizes, min_sizes)
        self.assertEqual(intervals[2], Interval(-7, -1))
        self.assertEqual(intervals[1], Interval(-1, 4))
        self.assertEqual(intervals[4], Interval(4, 7))
        self.assertIs(intervals[0], None)
        self.assertIs(intervals[3], None)

    def test_not_full(self):
        interval = Interval(0, 1.5)
        max_sizes = [1, 1]
        min_sizes = [1, 1]
        weights = [1.01, 0.99]
        intervals = distribute_intervals(interval, weights,
                                         max_sizes, min_sizes)
        self.assertEqual(intervals[0], Interval(0, 1))
        self.assertIs(intervals[1], None)

class SchedulerTests(unittest.TestCase):
    pass
