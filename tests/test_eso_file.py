"""Tests for DBEsoFile and DBEsoFileCollection ESO file reading.

Covers: parsing ESO files, get_results() filtering by variable, frequency,
units, date range (both-ends, start-only, end-only), alike matching, and
the top-level get_results() function accepting file paths and file instances.
Also tests DBEsoFileCollection list-like mutation methods and the error paths
of the top-level get_results() function for unsupported types and extensions.
"""
from datetime import datetime

import pytest

from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import RP, D, H, M
from db_eplusout_reader.db_esofile import DBEsoFile, DBEsoFileCollection


class TestEsofileReader:
    def test_process_eso_file(self, session_eso_file):
        assert session_eso_file.frequencies == [H, D, M, RP]

    def test_process_eso_file_collection(self, session_eso_file_collection):
        assert [f.environment_name for f in session_eso_file_collection] == [
            "UNTITLED (01-01:31-12)"
        ]


class TestEsoGetResults:
    def test_get_results_exact_match(self, session_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        results = session_eso_file.get_results(variables, H)

        assert len(results) == 1
        assert results.frequency == H
        var = results.first_variable
        assert var.key == "Environment"
        assert var.type == "Site Outdoor Air Drybulb Temperature"
        assert len(results.first_array) == 8760

    def test_get_results_alike(self, session_eso_file):
        variables = [Variable("Environment", "Drybulb", None)]
        results = session_eso_file.get_results(variables, H, alike=True)

        assert len(results) == 1
        var = results.first_variable
        assert "Drybulb" in var.type

    def test_get_results_all_variables(self, session_eso_file):
        variables = [Variable(None, None, None)]
        results = session_eso_file.get_results(variables, H)

        assert len(results) == 35

    def test_get_results_filter_by_units(self, session_eso_file):
        variables = [Variable(None, None, "C")]
        results = session_eso_file.get_results(variables, H)

        for var in results.variables:
            assert var.units == "C"

    def test_get_results_with_date_filter(self, session_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        start_date = datetime(2019, 1, 1, 1)
        end_date = datetime(2019, 1, 1, 23)

        results = session_eso_file.get_results(
            variables, H, start_date=start_date, end_date=end_date
        )

        assert len(results.first_array) == 23
        assert len(results.time_series) == 23

    def test_get_results_time_series(self, session_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        results = session_eso_file.get_results(variables, H)

        assert len(results.time_series) == 8760
        assert isinstance(results.time_series[0], datetime)

    def test_get_results_no_match(self, session_eso_file):
        variables = [Variable("NonExistent", "Variable", "X")]
        results = session_eso_file.get_results(variables, H)

        assert len(results) == 0

    def test_get_results_daily_frequency(self, session_eso_file):
        variables = [Variable(None, None, None)]
        results = session_eso_file.get_results(variables, D)

        assert results.frequency == D
        assert len(results.time_series) == 365

    def test_get_results_start_date_only(self, session_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        start_date = datetime(2019, 1, 15, 0)
        results = session_eso_file.get_results(variables, H, start_date=start_date)

        assert len(results.time_series) > 0
        assert all(ts >= start_date for ts in results.time_series)

    def test_get_results_end_date_only(self, session_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        end_date = datetime(2019, 1, 15, 23)
        results = session_eso_file.get_results(variables, H, end_date=end_date)

        assert len(results.time_series) > 0
        assert all(ts <= end_date for ts in results.time_series)


class TestCollectionMethods:
    def test_environment_names(self, session_eso_file_collection):
        names = session_eso_file_collection.environment_names
        assert isinstance(names, list)
        assert "UNTITLED (01-01:31-12)" in names

    def test_getitem(self, session_eso_file_collection):
        item = session_eso_file_collection[0]
        assert isinstance(item, DBEsoFile)

    def test_contains(self, session_eso_file_collection):
        item = session_eso_file_collection[0]
        assert item in session_eso_file_collection

    def test_append(self, session_eso_file):
        col = DBEsoFileCollection()
        col.append(session_eso_file)
        assert col[0] is session_eso_file

    def test_count_returns_none(self, session_eso_file):
        # count() is missing a return statement — it currently returns None
        col = DBEsoFileCollection([session_eso_file])
        assert col.count() is None

    def test_index(self, session_eso_file_collection):
        item = session_eso_file_collection[0]
        assert session_eso_file_collection.index(item) == 0

    def test_extend(self, session_eso_file):
        col = DBEsoFileCollection()
        col.extend([session_eso_file])
        assert col[0] is session_eso_file

    def test_insert(self, session_eso_file):
        col = DBEsoFileCollection([session_eso_file])
        col.insert(0, session_eso_file)
        assert len(list(col)) == 2

    def test_pop(self, session_eso_file):
        col = DBEsoFileCollection([session_eso_file])
        popped = col.pop(0)
        assert popped is session_eso_file
        assert len(list(col)) == 0

    def test_remove(self, session_eso_file):
        col = DBEsoFileCollection([session_eso_file])
        col.remove(session_eso_file)
        assert len(list(col)) == 0

    def test_reverse_does_not_mutate(self, session_eso_file):
        # reverse() calls reversed() but doesn't assign the result back —
        # the list remains unchanged (known bug)
        col = DBEsoFileCollection([session_eso_file, session_eso_file])
        original_first = col[0]
        col.reverse()
        assert col[0] is original_first  # unchanged

    def test_sort_raises_attribute_error(self, session_eso_file):
        # sort() references ef.file_name which does not exist on DBEsoFile
        col = DBEsoFileCollection([session_eso_file])
        with pytest.raises(AttributeError):
            col.sort(reverse=False)


class TestGetResultsFunction:
    def test_get_results_with_eso_path(self, eso_path):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        results = get_results(eso_path, variables, H)

        assert len(results) == 1
        assert results.frequency == H

    def test_get_results_with_eso_file_instance(self, session_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        results = get_results(session_eso_file, variables, H)

        assert len(results) == 1
        assert results.frequency == H

    def test_get_results_reuse_eso_file(self, session_eso_file):
        variables1 = [Variable(None, None, "C")]
        variables2 = [Variable(None, None, "Pa")]

        results1 = session_eso_file.get_results(variables1, H)
        results2 = session_eso_file.get_results(variables2, H)

        assert len(results1) > 0
        assert len(results2) > 0
        for var in results1.variables:
            assert var.units == "C"
        for var in results2.variables:
            assert var.units == "Pa"

    def test_get_results_unsupported_extension_raises(self, tmp_path):
        bad_path = str(tmp_path / "output.csv")
        variables = [Variable(None, None, None)]
        with pytest.raises(TypeError, match="Unsupported file type"):
            get_results(bad_path, variables, H)

    def test_get_results_with_collection_raises(self, session_eso_file_collection):
        variables = [Variable(None, None, None)]
        with pytest.raises(TypeError, match="DBEsoFileCollection"):
            get_results(session_eso_file_collection, variables, H)

    def test_get_results_unsupported_type_raises(self):
        variables = [Variable(None, None, None)]
        with pytest.raises(TypeError, match="Unsupported class"):
            get_results(42, variables, H)
