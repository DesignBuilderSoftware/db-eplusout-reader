from unittest import TestCase

from db_esofile_reader import Variable
from db_esofile_reader.constants import *
from db_esofile_reader.resutls_dict import ResultsDictionary, NoResults


class TestResultsDictionary(TestCase):
    def setUp(self):
        dct = {
            Variable(D, "Temperature", "Zone2", "C"): [22, 23, 19],
            Variable(D, "Temperature", "Zone1", "C"): [20, 21, 20],
            Variable(H, "Temperature", "Zone1", "C"): [24, 23, 20],
        }
        self.rd = ResultsDictionary()
        for k, v in dct.items():
            self.rd[k] = v

    def test_sorted_items(self):
        self.assertListEqual(
            [
                (Variable(D, "Temperature", "Zone1", "C"), [20, 21, 20]),
                (Variable(D, "Temperature", "Zone2", "C"), [22, 23, 19]),
                (Variable(H, "Temperature", "Zone1", "C"), [24, 23, 20]),
            ],
            self.rd.sorted_items
        )

    def test_empty_sorted_items(self):
        rd = ResultsDictionary()
        with self.assertRaises(NoResults):
            _ = rd.sorted_items

    def test_scalar(self):
        self.assertEqual(20, self.rd.scalar)

    def test_no_scalar(self):
        rd = ResultsDictionary()
        rd[Variable(D, "Temperature", "Zone1", "C")] = []
        with self.assertRaises(NoResults):
            _ = rd.scalar

    def test_first_array(self):
        self.assertListEqual([20, 21, 20], self.rd.first_array)

    def test_first_variable(self):
        self.assertTupleEqual(Variable(D, "Temperature", "Zone1", "C"), self.rd.first_variable)

    def test_variables(self):
        self.assertListEqual(
            [
                Variable(D, "Temperature", "Zone1", "C"),
                Variable(D, "Temperature", "Zone2", "C"),
                Variable(H, "Temperature", "Zone1", "C"),
            ],
            self.rd.variables
        )

    def test_arrays(self):
        self.assertListEqual([[20, 21, 20], [22, 23, 19], [24, 23, 20]], self.rd.arrays)
