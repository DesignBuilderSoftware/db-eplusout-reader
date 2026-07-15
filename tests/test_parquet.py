"""Tests for the optional Parquet I/O extension.

Skipped entirely when pyarrow (the 'parquet' extra) is not installed.
Covers round-tripping a ResultsDictionary to Parquet and back via the
to_parquet / read_parquet functions, including frequency, variables,
arrays and time series.
"""

from datetime import datetime

import pytest

pytest.importorskip("pyarrow")

from db_eplusout_reader import Variable, get_results, read_parquet, to_parquet
from db_eplusout_reader.constants import H
from db_eplusout_reader.results_dict import ResultsDictionary

_DRYBULB = Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")


@pytest.fixture
def float_results():
    rd = ResultsDictionary(frequency=H)
    rd.time_series = [datetime(2002, 1, 1, 1), datetime(2002, 1, 1, 2), datetime(2002, 1, 1, 3)]
    rd[Variable("ZONE1", "Zone Mean Air Temperature", "C")] = [20.0, 21.0, 20.5]
    rd[Variable("ZONE2", "Zone Mean Air Temperature", "C")] = [22.0, 23.0, 19.0]
    return rd


class TestParquetRoundTrip:
    def test_round_trip(self, float_results, tmp_path):
        path = tmp_path / "results.parquet"
        to_parquet(float_results, path)
        loaded = read_parquet(path)

        assert loaded.frequency == float_results.frequency
        assert loaded.variables == float_results.variables
        assert loaded.arrays == float_results.arrays
        assert loaded.time_series == float_results.time_series

    def test_round_trip_from_sql(self, sql_path, tmp_path):
        rd = get_results(sql_path, _DRYBULB, frequency=H)
        path = tmp_path / "sql.parquet"
        to_parquet(rd, path)
        loaded = read_parquet(path)

        assert loaded.frequency == rd.frequency
        assert loaded.first_variable == _DRYBULB
        assert loaded.first_array == rd.first_array
        assert loaded.time_series == rd.time_series

    def test_round_trip_without_time_series(self, tmp_path):
        rd = ResultsDictionary(frequency=H)
        rd[_DRYBULB] = [1.0, 2.0, 3.0]
        path = tmp_path / "no_time.parquet"
        to_parquet(rd, path)
        loaded = read_parquet(path)

        assert loaded.time_series is None
        assert loaded[_DRYBULB] == [1.0, 2.0, 3.0]

    def test_duplicate_variables_preserved(self, tmp_path):
        # variables with identical (key, type, units) must both survive
        rd = ResultsDictionary(frequency=H)
        same = Variable("ZONE1", "Zone Mean Air Temperature", "C")
        rd[same] = [1.0, 2.0]
        path = tmp_path / "dup.parquet"
        to_parquet(rd, path)
        loaded = read_parquet(path)
        assert loaded[same] == [1.0, 2.0]

    def test_compression_kwarg_forwarded(self, float_results, tmp_path):
        path = tmp_path / "compressed.parquet"
        to_parquet(float_results, path, compression="gzip")  # must not raise
        loaded = read_parquet(path)
        assert loaded.arrays == float_results.arrays
