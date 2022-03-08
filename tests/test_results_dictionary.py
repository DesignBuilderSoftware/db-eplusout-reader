import csv
from datetime import datetime

import pytest

from db_eplusout_reader import Variable
from db_eplusout_reader.constants import H
from db_eplusout_reader.exceptions import InvalidShape, NoResults
from db_eplusout_reader.results_dict import ResultsDictionary, ResultsHandler


class TestResultsDictionary:
    @pytest.fixture(scope="function")
    def test_results(self):
        return [
            ["", "Temperature", "Temperature", "Temperature"],
            ["", "Zone2", "Zone1", "Zone3"],
            ["", "C", "C", "C"],
            ["2002-01-01 00:00:00", "22", "20", "19"],
            ["2002-01-02 00:00:00", "23", "21", "23"],
            ["2002-01-03 00:00:00", "19", "20", "20"],
        ]

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

    @pytest.mark.parametrize("delimiter", [",", ";", "\t", " "])
    def test_to_csv(self, results_dictionary, temp_csv, delimiter, test_results):
        results_dictionary.to_csv(temp_csv, delimiter=delimiter)
        with open(temp_csv) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=delimiter)
            assert list(csv_reader) == test_results

    @pytest.mark.parametrize("delimiter", [",", ";", "\t", " "])
    def test_to_csv_title_row(
        self, results_dictionary, temp_csv, delimiter, test_results
    ):
        results_dictionary.to_csv(temp_csv, delimiter=delimiter, title="TEST TITLE")
        with open(temp_csv) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=delimiter)
            assert list(csv_reader) == [["TEST TITLE"]] + test_results

    @pytest.mark.parametrize("delimiter", [",", ";", "\t", " "])
    def test_to_csv_append(self, results_dictionary, temp_csv, delimiter, test_results):
        results_dictionary.to_csv(temp_csv, delimiter=delimiter)
        results_dictionary.to_csv(
            temp_csv, delimiter=delimiter, append=True, title="FOO"
        )
        with open(temp_csv) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=delimiter)
            assert list(csv_reader) == test_results + [["FOO"]] + test_results

    @pytest.mark.parametrize(
        "explode, expected",
        [
            (
                True,
                [
                    ["", "Temperature", "Temperature", "Temperature"],
                    ["", "Zone2", "Zone1", "Zone3"],
                    ["", "C", "C", "C"],
                    ["2002-01-01 00:00:00", "22", "20", "19"],
                    ["2002-01-02 00:00:00", "23", "21", "23"],
                    ["2002-01-03 00:00:00", "19", "20", "20"],
                ],
            ),
            (
                False,
                [
                    [
                        "",
                        "Variable(key='Temperature', type='Zone2', units='C')",
                        "Variable(key='Temperature', type='Zone1', units='C')",
                        "Variable(key='Temperature', type='Zone3', units='C')",
                    ],
                    ["2002-01-01 00:00:00", "22", "20", "19"],
                    ["2002-01-02 00:00:00", "23", "21", "23"],
                    ["2002-01-03 00:00:00", "19", "20", "20"],
                ],
            ),
        ],
    )
    def test_to_csv_explode_header(
        self, results_dictionary, temp_csv, explode, expected
    ):
        results_dictionary.to_csv(temp_csv, explode_header=explode)
        with open(temp_csv) as csv_file:
            csv_reader = csv.reader(csv_file)
            assert list(csv_reader) == expected

    def test_get_table_shape(self, results_dictionary):
        table = results_dictionary.to_table()
        assert ResultsHandler.get_table_shape(table) == (6, 4)

    def test_get_table_shape_invalid(self):
        table = [[1, 2, 3], [1, 2], [1, 2, 3]]
        with pytest.raises(InvalidShape):
            _ = ResultsHandler.get_table_shape(table)
