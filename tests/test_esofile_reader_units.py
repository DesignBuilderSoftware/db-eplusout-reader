"""Unit tests for individual parsing helpers in the esofile_reader module.

Complements the file level tests in test_esofile_reader.py with direct
checks of line parsing helpers (statement, header, frequency lines) and
the InvalidLineSyntax error path in the file body.
"""

from datetime import datetime

import pytest

from db_eplusout_reader.exceptions import InvalidLineSyntax
from db_eplusout_reader.processing.esofile_reader import (
    ANNUAL_LINE,
    DAILY_LINE,
    MONTHLY_LINE,
    RUNPERIOD_LINE,
    TIMESTEP_OR_HOURLY_LINE,
    Variable,
    get_eso_file_timestamp,
    get_eso_file_version,
    process_eso_file,
    process_header_line,
    process_month_rp_frequency_line,
    process_statement_line,
    process_ts_h_d_frequency_line,
    split_raw_line,
)
from db_eplusout_reader.processing.esofile_time import EsoTimestamp

_STATEMENT = "Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2020.11.10 11:31\n"


class TestStatementLine:
    def test_get_eso_file_version(self):
        assert get_eso_file_version(" Version 9.2.0-921312fa1d") == 920

    def test_get_eso_file_timestamp(self):
        timestamp = get_eso_file_timestamp(" YMD=2020.11.10 11:31")
        assert timestamp == datetime(2020, 11, 10, 11, 31)

    def test_process_statement_line(self):
        version, timestamp = process_statement_line(_STATEMENT)
        assert version == 920
        assert timestamp == datetime(2020, 11, 10, 11, 31)


class TestHeaderLine:
    def test_standard_variable_line(self):
        line = "7,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Hourly\n"
        assert process_header_line(line) == (
            7,
            "Environment",
            "Site Outdoor Air Drybulb Temperature",
            "C",
            "hourly",
        )

    def test_meter_line(self):
        line = "365,1,Electricity:Facility [J] !Hourly\n"
        line_id, key, type_, units, frequency = process_header_line(line)
        assert (line_id, key, type_, units) == (365, "Meter", "Electricity:Facility", "J")
        assert frequency == "hourly"

    def test_cumulative_meter_line(self):
        line = "366,1,Cumulative Electricity:Facility [J] !RunPeriod\n"
        line_id, key, type_, units, frequency = process_header_line(line)
        assert key == "Cumulative Meter"
        assert type_ == "Cumulative Electricity:Facility"
        assert frequency == "runperiod"

    def test_invalid_line_raises_attribute_error(self):
        with pytest.raises(AttributeError):
            process_header_line("certainly not a header line\n")


class TestFrequencyLines:
    def test_hourly_line(self):
        data = ["1", " 1", " 1", " 0", " 1", " 0.00", "60.00", "Tuesday\n"]
        frequency, date, day = process_ts_h_d_frequency_line(TIMESTEP_OR_HOURLY_LINE, data)
        assert frequency == "hourly"
        assert date == EsoTimestamp(1, 1, 1, 60)
        assert day == "Tuesday"

    def test_timestep_line(self):
        data = ["1", " 1", " 1", " 0", " 1", "30.00", "60.00", "Tuesday\n"]
        frequency, date, day = process_ts_h_d_frequency_line(TIMESTEP_OR_HOURLY_LINE, data)
        assert frequency == "timestep"
        assert date == EsoTimestamp(1, 1, 1, 60)
        assert day == "Tuesday"

    def test_daily_line(self):
        data = ["1", " 2", " 28", " 0", "Wednesday\n"]
        frequency, date, day = process_ts_h_d_frequency_line(DAILY_LINE, data)
        assert frequency == "daily"
        assert date == EsoTimestamp(2, 28, 0, 0)
        assert day == "Wednesday"

    def test_monthly_line(self):
        frequency, date, n_days = process_month_rp_frequency_line(MONTHLY_LINE, ["31", "1"])
        assert frequency == "monthly"
        assert date == EsoTimestamp(1, 1, 0, 0)
        assert n_days == 31

    def test_runperiod_line(self):
        frequency, date, n_days = process_month_rp_frequency_line(RUNPERIOD_LINE, ["365"])
        assert frequency == "runperiod"
        assert date == EsoTimestamp(1, 1, 0, 0)
        assert n_days == 365

    def test_annual_line(self):
        frequency, date, n_days = process_month_rp_frequency_line(ANNUAL_LINE, ["2013"])
        assert frequency == "annual"
        assert date == EsoTimestamp(1, 1, 0, 0)
        assert n_days is None


class TestSplitRawLine:
    def test_split_raw_line(self):
        line_id, line = split_raw_line("7,20.0\n")
        assert line_id == 7
        assert line == ["20.0\n"]


class TestBodyErrors:
    def test_invalid_syntax_in_body(self, tmp_path):
        header = (
            _STATEMENT
            + "1,5,Environment Title[],Latitude[deg],Longitude[deg],Time Zone[],Elevation[m]\n"  # noqa: E501
            + "2,8,Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],Hour[],StartMinute[],EndMinute[],DayType\n"  # noqa: E501
            + "3,5,Cumulative Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],DayType\n"  # noqa: E501
            + "4,2,Cumulative Days of Simulation[],Month[]\n"
            + "5,1,Cumulative Days of Simulation[]\n"
            + "6,1,Calendar Year of Simulation[]\n"
            + "7,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Hourly\n"
            + "End of Data Dictionary\n"
        )
        eso = tmp_path / "bad_body.eso"
        eso.write_text(
            header + "1,TEST ENV, 0.0, 0.0, 0.0, 0.0\n" + "??? invalid body line ???\n"
        )
        with pytest.raises(InvalidLineSyntax, match="Unexpected line syntax"):
            process_eso_file(str(eso))


class TestVariableNamedTuple:
    def test_fields(self):
        assert Variable._fields == ("key", "type", "units")
