from datetime import datetime

import pytest

from db_eplusout_reader import Variable
from db_eplusout_reader.constants import H
from db_eplusout_reader.results_dict import NoResults, ResultsDictionary, ResultsHandler


class TestResultsDictionary:
    def test_items(self, results_dictionary):
        assert list(results_dictionary.items()) == [
            (Variable("Temperature", "Zone2", "C"), [22, 23, 19]),
            (Variable("Temperature", "Zone1", "C"), [20, 21, 20]),
            (Variable("Temperature", "Zone3", "C"), [19, 23, 20]),
        ]

    def test_empty_sorted_items(self):
        rd = ResultsDictionary()
        with pytest.raises(NoResults):
            _ = rd._items

    def test_scalar(self, results_dictionary):
        assert results_dictionary.scalar == 22

    def test_no_scalar(self):
        rd = ResultsDictionary()
        rd[Variable("Temperature", "Zone1", "C")] = []
        with pytest.raises(NoResults):
            _ = rd.scalar

    def test_first_array(self, results_dictionary):
        assert results_dictionary.first_array == [22, 23, 19]

    def test_first_variable(self, results_dictionary):
        assert results_dictionary.first_variable == Variable(
            "Temperature", "Zone2", "C"
        )

    def test_variables(self, results_dictionary):
        assert results_dictionary.variables == [
            Variable("Temperature", "Zone2", "C"),
            Variable("Temperature", "Zone1", "C"),
            Variable("Temperature", "Zone3", "C"),
        ]

    def test_arrays(self, results_dictionary):
        assert results_dictionary.arrays == [[22, 23, 19], [20, 21, 20], [19, 23, 20]]

    def test_time_series(self, results_dictionary):
        assert results_dictionary.time_series == [
            datetime(2002, 1, 1, 0),
            datetime(2002, 1, 2, 0),
            datetime(2002, 1, 3, 0),
        ]

    def test_frequency(self, results_dictionary):
        assert results_dictionary.frequency == H

    @pytest.mark.parametrize(
        "explode, n_rows, n_columns", [(True, 6, 4), (False, 4, 4)]
    )
    def test_to_table(self, results_dictionary, explode, n_rows, n_columns):
        table = results_dictionary.to_table(explode_header=explode)
        assert len(table) == n_rows
        for row in table:
            assert len(row) == n_columns

    @pytest.mark.parametrize(
        "explode, n_rows, n_columns", [(True, 6, 3), (False, 4, 3)]
    )
    def test_to_table_no_index(self, results_dictionary, explode, n_rows, n_columns):
        results_dictionary.time_series = None
        table = results_dictionary.to_table(explode_header=explode)
        assert len(table) == n_rows
        for row in table:
            assert len(row) == n_columns

    def test_to_csv(self):

        table = ResultsHandler.convert_dict_to_table(self.rd)
        print(table)
