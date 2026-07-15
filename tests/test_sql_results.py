"""Tests for SQL output file reading via get_results() and sql_reader internals.

Covers: exact-match / alike / all-variable queries, date-range slicing,
meter results, time-series length across all frequencies (RP/M/D/H), the
get_timestamps_from_sql helper, IOError for missing files, and internal
helpers to_eso_frequency, to_sql_frequency, and validate_time.
"""

import os.path
from datetime import datetime

import pytest

from db_eplusout_reader import (
    Variable,
    get_all_variables,
    get_results,
    get_tables,
    get_variables,
)
from db_eplusout_reader.constants import RP, TS, A, D, H, M
from db_eplusout_reader.results_dict import ResultsHandler
from db_eplusout_reader.sql_reader import (
    get_timestamps_from_sql,
    to_eso_frequency,
    to_sql_frequency,
    validate_time,
)

# Variable present in all versioned 1ZoneUncontrolled SQL files
_DRYBULB = Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")


class TestSql:
    def test_get_results_exact_match(self, sql_path):
        variable = Variable("ZONE ONE", "Zone Mean Air Temperature", "C")
        results = get_results(sql_path, variable, frequency=H)
        assert [variable] == list(results.keys())
        # 8808 = 8760 run-period hours + 48 design-day hours (2 × 24)
        assert len(results[variable]) == 8808

    def test_get_results_multiple_variables(self, sql_path):
        variables = [
            Variable("ZN001:WALL001", "Surface Inside Face Temperature", "C"),
            Variable("ZN001:WALL001", "Surface Outside Face Temperature", "C"),
        ]
        results = get_results(sql_path, variables, frequency=D)
        assert variables == list(results.keys())
        # 367 = 365 run-period days + 2 design days
        assert all(len(v) == 367 for v in results.values())

    def test_get_results_alike(self, sql_path):
        variable = Variable("ZONE ONE", "Zone Mean", "C")
        results = get_results(sql_path, variable, frequency=H, alike=True)
        assert len(results) >= 2
        for var in results.variables:
            assert "ZONE ONE" in var.key
            assert "Zone Mean" in var.type

    def test_get_all_results(self, sql_path):
        variable = Variable(None, None, None)
        results = get_results(sql_path, variable, H, alike=True)
        assert len(results.keys()) > 0

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
        assert len(results.keys()) > 0
        assert len(results.first_array) == 31 * 24

    def test_get_results_start_end_dates(self, sql_path):
        results = get_results(
            sql_path,
            variables=_DRYBULB,
            frequency=H,
            alike=False,
            start_date=datetime(2013, 5, 31, 0),
            end_date=datetime(2013, 5, 31, 23, 59),
        )
        assert len(list(results.values())[0]) == 24

    def test_get_timestamps_monthly(self, sql_path):
        timestamps = get_timestamps_from_sql(sql_path, "monthly")
        # includes design-day months (Dec, Jul) + 12 run-period months
        assert len(timestamps) in {12, 14}
        assert all(isinstance(ts, datetime) for ts in timestamps)

    def test_get_results_meter(self, sql_path):
        variable = Variable("ZONE ONE", "Zone Other Equipment Total Heating Energy", "J")
        results = get_results(sql_path, variables=variable, frequency=RP)
        assert len(results) == 1
        assert len(list(results.values())[0]) > 0

    def test_meter_null_keyvalue_is_empty_string(self, sql_path):
        # Since EnergyPlus 23.1 meter KeyValue is stored as NULL. The returned
        # Variable key must be an empty string, not the literal "None" (#12).
        results = get_results(
            sql_path, Variable(None, "EnergyTransfer:Facility", "J"), frequency=H
        )
        assert len(results) == 1
        assert results.first_variable.key == ""
        assert len(results.first_array) > 0

    def test_results_time_series(self, sql_path):
        variable = Variable("ZONE ONE", "Zone Other Equipment Total Heating Energy", "J")
        for frequency, expected in zip([RP, M, D, H], [3, 14, 367, 8808]):
            results_dictionary = get_results(sql_path, variable, frequency=frequency)
            assert len(results_dictionary.time_series) == expected

    def test_results_to_csv(self, sql_path):
        results_dictionary = get_results(sql_path, Variable(None, None, None), frequency=M)
        rows, cols = ResultsHandler.get_table_shape(results_dictionary.to_table())
        n_vars = len(results_dictionary)
        n_times = len(results_dictionary.time_series)
        assert rows == n_times + 3  # header + 2 label rows
        assert cols == n_vars + 1  # +1 for time column

    def test_invalid_file_path(self, test_files_dir):
        variable = Variable("ZONE ONE", "Zone Mean Air Temperature", "C")
        invalid_path = os.path.join(test_files_dir, "invalid_file.sql")
        with pytest.raises(IOError):
            get_results(invalid_path, variables=variable, frequency=H)
        assert not os.path.exists(invalid_path)


class TestListVariables:
    def test_get_tables(self, any_sql_path):
        tables = get_tables(any_sql_path)
        assert len(tables) > 0
        # frequencies are returned as eso constants and de-duplicated
        assert len(tables) == len(set(tables))
        assert {H, D}.issubset(set(tables))

    def test_get_variables_for_frequency(self, sql_path):
        variables = get_variables(sql_path, H)
        assert len(variables) > 0
        assert all(isinstance(v, Variable) for v in variables)
        assert _DRYBULB in variables
        # sorted and unique
        assert variables == sorted(variables)

    def test_listed_variable_is_retrievable(self, sql_path):
        # a listed (non-meter) variable can be fetched via get_results
        variables = get_variables(sql_path, H)
        assert _DRYBULB in variables
        results = get_results(sql_path, _DRYBULB, frequency=H)
        assert results.first_variable == _DRYBULB

    def test_get_all_variables(self, sql_path):
        overview = get_all_variables(sql_path)
        assert set(overview.keys()) == set(get_tables(sql_path))
        for frequency, variables in overview.items():
            assert variables == get_variables(sql_path, frequency)

    def test_get_tables_missing_file(self, test_files_dir):
        with pytest.raises(IOError):
            get_tables(os.path.join(test_files_dir, "nope.sql"))


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
