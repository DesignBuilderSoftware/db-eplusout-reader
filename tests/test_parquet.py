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

    def test_none_variable_fields_round_trip_as_empty_strings(self, tmp_path):
        # Variable fields may legitimately be None (e.g. wildcard queries via
        # get_results), but Arrow metadata only stores bytes, so _encode()
        # maps None -> b"". On read-back this becomes "" rather than None.
        # This is a documented lossy-round-trip quirk of the format, not
        # something being asserted as a bug: callers that rely on None
        # surviving a to_parquet/read_parquet round trip will be surprised.
        rd = ResultsDictionary(frequency=H)
        rd[Variable(None, None, None)] = [1.0, 2.0]
        path = tmp_path / "none_fields.parquet"
        to_parquet(rd, path)
        loaded = read_parquet(path)

        assert loaded.first_variable == Variable("", "", "")
        assert loaded.first_array == [1.0, 2.0]

    def test_empty_time_series_list_omits_timestamp_column(self, tmp_path):
        # An empty list is falsy, same code path as time_series=None.
        rd = ResultsDictionary(frequency=H)
        rd.time_series = []
        rd[_DRYBULB] = [1.0]
        path = tmp_path / "empty_ts.parquet"
        to_parquet(rd, path)
        loaded = read_parquet(path)
        assert loaded.time_series is None

    def test_frequency_defaults_to_empty_string_when_metadata_absent(self, tmp_path):
        # If a Parquet file has no db_schema frequency metadata at all
        # (e.g. written by some other tool), read_parquet should not blow up
        # and should fall back to "".
        import pyarrow as pa
        import pyarrow.parquet as pq

        field = pa.field(
            "ZONE1|Zone Mean Air Temperature|C",
            pa.float64(),
            metadata={b"db_role": b"variable", b"key": b"ZONE1"},
        )
        schema = pa.schema([field])  # no frequency metadata on the schema
        table = pa.table([pa.array([1.0, 2.0])], schema=schema)
        path = tmp_path / "no_frequency.parquet"
        pq.write_table(table, path)

        loaded = read_parquet(path)
        assert loaded.frequency == ""
        assert loaded.first_array == [1.0, 2.0]

    def test_multiple_variables_and_overwrite_existing_file(self, float_results, tmp_path):
        # Writing to an already-existing path should just overwrite it, and
        # multiple distinct variables plus a time series should all survive.
        path = tmp_path / "overwrite.parquet"
        to_parquet(float_results, path)
        assert path.exists()

        smaller = ResultsDictionary(frequency=H)
        smaller[_DRYBULB] = [5.0]
        to_parquet(smaller, path)

        loaded = read_parquet(path)
        assert loaded.variables == [_DRYBULB]
        assert loaded.first_array == [5.0]
        assert loaded.time_series is None


class TestMissingPyarrowExtra:
    """Exercise the `pa is None` guard without needing to actually uninstall pyarrow."""

    def test_require_pyarrow_raises_when_extra_not_installed(self, monkeypatch):
        import db_eplusout_reader.parquet as parquet_module

        monkeypatch.setattr(parquet_module, "pa", None)
        with pytest.raises(ImportError, match="pip install db-eplusout-reader\\[parquet\\]"):
            parquet_module._require_pyarrow()

    def test_to_parquet_raises_import_error_without_pyarrow(
        self, float_results, tmp_path, monkeypatch
    ):
        import db_eplusout_reader.parquet as parquet_module

        monkeypatch.setattr(parquet_module, "pa", None)
        monkeypatch.setattr(parquet_module, "pq", None)
        path = tmp_path / "should_not_be_created.parquet"
        with pytest.raises(ImportError, match="optional 'parquet' extra"):
            to_parquet(float_results, path)
        assert not path.exists()

    def test_read_parquet_raises_import_error_without_pyarrow(self, tmp_path, monkeypatch):
        import db_eplusout_reader.parquet as parquet_module

        monkeypatch.setattr(parquet_module, "pa", None)
        monkeypatch.setattr(parquet_module, "pq", None)
        # File need not even exist: the guard must fire before any I/O is attempted.
        path = tmp_path / "does_not_exist.parquet"
        with pytest.raises(ImportError, match="optional 'parquet' extra"):
            read_parquet(path)
