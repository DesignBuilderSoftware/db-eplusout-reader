"""Tests for SQL output file reading via get_results() and sql_reader internals.

Covers: exact-match / alike / all-variable queries, date-range slicing,
meter results, time-series length across all frequencies (RP/M/D/H), the
get_timestamps_from_sql helper, IOError for missing files, and internal
helpers to_eso_frequency, to_sql_frequency, and validate_time.
"""
import os.path
from datetime import datetime

import pytest

from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import RP, TS, A, D, H, M
from db_eplusout_reader.results_dict import ResultsHandler
from db_eplusout_reader.sql_reader import get_timestamps_from_sql, to_eso_frequency, to_sql_frequency, validate_time


class TestSql:
    def test_get_results_exact_match(self, sql_path):
        variable = Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", "")
        results = get_results(sql_path, variable, frequency=H)
        assert [variable] == list(results.keys()), [variable]
        assert 8760 == len(results[variable])

    def test_get_results_multiple_variables(self, sql_path):
        variables = [
            Variable("BLOCK1:ZONE2", "Zone Air Relative Humidity", "%"),
            Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
        ]
        results = get_results(sql_path, variables, frequency=D)
        assert variables == list(results.keys()), variables
        assert all(map(lambda x: len(x) == 365, results.values()))

    def test_get_results_alike(self, sql_path):
        variable = Variable("PEOPLE BLOCK", "Zone Thermal Comfort Fanger Model", "")
        results = get_results(sql_path, variable, frequency=H, alike=True)
        expected = [
            Variable("PEOPLE BLOCK1:ZONE1", "Zone Thermal Comfort Fanger Model PMV", ""),
            Variable("PEOPLE BLOCK1:ZONE1", "Zone Thermal Comfort Fanger Model PPD", "%"),
            Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
            Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PPD", "%"),
        ]
        assert list(results.keys()) == expected

    def test_get_all_results(self, sql_path):
        variable = Variable(None, None, None)
        results = get_results(sql_path, variable, H, alike=True)
        assert len(results.keys()) == 35

    def test_get_all_sliced_results(self, sql_path):
        variable = Variable(None, None, None)
        results = get_results(
            sql_path,
            variable,
            frequency=H,
            alike=False,
            start_date=datetime(2013, 1, 1),
            end_date=datetime(2013, 2, 1),
        )
        assert len(results.keys()) == 35
        assert len(results.first_array) == 31 * 24

    def test_get_results_start_end_dates(self, sql_path):
        variable = Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PPD", "%")
        results = get_results(
            sql_path,
            variables=variable,
            frequency=H,
            alike=False,
            start_date=datetime(2013, 5, 31, 0),
            end_date=datetime(2013, 5, 31, 23, 59),
        )
        assert len(list(results.values())[0]) == 24

    def test_get_timestamps_monthly(self, sql_path):
        timestamps = get_timestamps_from_sql(sql_path, "monthly")
        assert timestamps == [datetime(2013, i, 1) for i in range(1, 13)]

    def test_get_results_meter(self, sql_path):
        variable = Variable("", "DistrictHeating:Facility", "J")
        results = get_results(sql_path, variables=variable, frequency=RP)
        assert {variable: [30475176136.970848]} == results

    def test_results_time_series(self, sql_path):
        for frequency, expected in zip([RP, M, D, H], [1, 12, 365, 8760]):
            results_dictionary = get_results(
                sql_path,
                Variable("", "DistrictHeating:Facility", "J"),
                frequency=frequency,
            )
            assert len(results_dictionary.time_series) == expected

    def test_results_to_csv(self, sql_path):
        results_dictionary = get_results(sql_path, Variable(None, None, None), frequency=M)
        assert ResultsHandler.get_table_shape(results_dictionary.to_table()) == (15, 36)

    def test_invalid_file_path(self, test_files_dir):
        variable = Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PPD", "%")
        invalid_path = os.path.join(test_files_dir, "invalid_file.sql")
        with pytest.raises(IOError):
            get_results(invalid_path, variables=variable, frequency=H)
        assert not os.path.exists(invalid_path)


class TestSqlInternals:
    def test_to_eso_frequency_all(self):
        assert to_eso_frequency("Zone Timestep") == TS
        assert to_eso_frequency("Hourly") == H
        assert to_eso_frequency("Daily") == D
        assert to_eso_frequency("Monthly") == M
        assert to_eso_frequency("Run Period") == RP
        assert to_eso_frequency("Annual") == A
        assert to_eso_frequency("HVAC System Timestep") == TS

    def test_to_sql_frequency_none(self):
        assert to_sql_frequency(None) is None

    def test_to_sql_frequency_all(self):
        assert to_sql_frequency(TS) == "Zone Timestep"
        assert to_sql_frequency(H) == "Hourly"
        assert to_sql_frequency(D) == "Daily"
        assert to_sql_frequency(M) == "Monthly"
        assert to_sql_frequency(RP) == "Run Period"
        assert to_sql_frequency(A) == "Annual"

    def test_validate_time_start_only(self):
        ts = datetime(2013, 5, 15, 12)
        start = datetime(2013, 5, 1)
        assert validate_time(ts, start, None) is True
        assert validate_time(datetime(2013, 4, 30), start, None) is False

    def test_validate_time_end_only(self):
        ts = datetime(2013, 5, 15, 12)
        end = datetime(2013, 5, 31)
        assert validate_time(ts, None, end) is True
        assert validate_time(datetime(2013, 6, 1), None, end) is False

    def test_validate_time_neither(self):
        ts = datetime(2013, 5, 15, 12)
        assert validate_time(ts, None, None) is True
