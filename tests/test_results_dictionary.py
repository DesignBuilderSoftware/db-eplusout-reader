from unittest import TestCase

from db_eplusout_reader import Variable
from db_eplusout_reader.constants import *
from db_eplusout_reader.results_dict import ResultsDictionary, NoResults


class TestResultsDictionary(TestCase):
    def setUp(self):
        self.rd = ResultsDictionary()
        self.rd[Variable(D, "Temperature", "Zone2", "C")] = [22, 23, 19]
        self.rd[Variable(D, "Temperature", "Zone1", "C")] = [20, 21, 20]
        self.rd[Variable(H, "Temperature", "Zone1", "C")] = [24, 23, 20]

    def test_items(self):
        self.assertListEqual(
            [
                (Variable(D, "Temperature", "Zone2", "C"), [22, 23, 19]),
                (Variable(D, "Temperature", "Zone1", "C"), [20, 21, 20]),
                (Variable(H, "Temperature", "Zone1", "C"), [24, 23, 20]),
            ],
            list(self.rd.items())
        )

    def test_empty_sorted_items(self):
        rd = ResultsDictionary()
        with self.assertRaises(NoResults):
            _ = rd._items

    def test_scalar(self):
        self.assertEqual(22, self.rd.scalar)

    def test_no_scalar(self):
        rd = ResultsDictionary()
        rd[Variable(D, "Temperature", "Zone1", "C")] = []
        with self.assertRaises(NoResults):
            _ = rd.scalar

    def test_first_array(self):
        self.assertListEqual([22, 23, 19], self.rd.first_array)

    def test_first_variable(self):
        self.assertTupleEqual(Variable(D, "Temperature", "Zone2", "C"), self.rd.first_variable)

    def test_variables(self):
        self.assertListEqual(
            [
                Variable(D, "Temperature", "Zone2", "C"),
                Variable(D, "Temperature", "Zone1", "C"),
                Variable(H, "Temperature", "Zone1", "C"),
            ],
            self.rd.variables
        )

    def test_arrays(self):
        self.assertListEqual([[22, 23, 19], [20, 21, 20], [24, 23, 20]], self.rd.arrays)
