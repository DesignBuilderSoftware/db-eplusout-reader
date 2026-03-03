from datetime import datetime

from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import RP, D, H, M


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
