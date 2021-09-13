from datetime import datetime
from unittest import TestCase

from db_eplusout_reader import Variable
from db_eplusout_reader.constants import H
from db_eplusout_reader.results_dict import NoResults, ResultsDictionary


class TestResultsDictionary(TestCase):
    def setUp(self):
        self.rd = ResultsDictionary(frequency=H)
        self.rd.time_series = [
            datetime(2002, 1, 1, 0),
            datetime(2002, 1, 2, 0),
            datetime(2002, 1, 3, 0),
        ]
        self.rd[Variable("Temperature", "Zone2", "C")] = [22, 23, 19]
        self.rd[Variable("Temperature", "Zone1", "C")] = [20, 21, 20]
        self.rd[Variable("Temperature", "Zone3", "C")] = [19, 23, 20]

    def test_items(self):
        self.assertListEqual(
            [
                (Variable("Temperature", "Zone2", "C"), [22, 23, 19]),
                (Variable("Temperature", "Zone1", "C"), [20, 21, 20]),
                (Variable("Temperature", "Zone3", "C"), [19, 23, 20]),
            ],
            list(self.rd.items()),
        )

    def test_empty_sorted_items(self):
        rd = ResultsDictionary()
        with self.assertRaises(NoResults):
            _ = rd._items

    def test_scalar(self):
        self.assertEqual(22, self.rd.scalar)

    def test_no_scalar(self):
        rd = ResultsDictionary()
        rd[Variable("Temperature", "Zone1", "C")] = []
        with self.assertRaises(NoResults):
            _ = rd.scalar

    def test_first_array(self):
        self.assertListEqual([22, 23, 19], self.rd.first_array)

    def test_first_variable(self):
        self.assertTupleEqual(
            Variable("Temperature", "Zone2", "C"), self.rd.first_variable
        )

    def test_variables(self):
        self.assertListEqual(
            [
                Variable("Temperature", "Zone2", "C"),
                Variable("Temperature", "Zone1", "C"),
                Variable("Temperature", "Zone3", "C"),
            ],
            self.rd.variables,
        )

    def test_arrays(self):
        self.assertListEqual([[22, 23, 19], [20, 21, 20], [19, 23, 20]], self.rd.arrays)

    def test_time_series(self):
        self.assertListEqual(
            [
                datetime(2002, 1, 1, 0),
                datetime(2002, 1, 2, 0),
                datetime(2002, 1, 3, 0),
            ],
            self.rd.time_series,
        )

    def test_frequency(self):
        self.assertEqual(H, self.rd.frequency)
