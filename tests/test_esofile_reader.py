"""Tests for low-level ESO file parsing in esofile_reader module.

Covers error paths: BlankLineError for blank lines in header and body,
InvalidLineSyntax for unexpected header lines, and IncompleteFile when
the file is truncated before the 'End of Data' marker.
"""

import pytest

from db_eplusout_reader.exceptions import (
    BlankLineError,
    IncompleteFile,
    InvalidLineSyntax,
)
from db_eplusout_reader.processing.esofile_reader import process_eso_file

_HEADER = (
    "Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2020.11.10 11:31\n"
    "1,5,Environment Title[],Latitude[deg],Longitude[deg],Time Zone[],Elevation[m]\n"
    "2,8,Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],Hour[],StartMinute[],EndMinute[],DayType\n"  # noqa: E501
    "3,5,Cumulative Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],DayType  ! When Daily Report Variables Requested\n"  # noqa: E501
    "4,2,Cumulative Days of Simulation[],Month[]  ! When Monthly Report Variables Requested\n"
    "5,1,Cumulative Days of Simulation[] ! When Run Period Report Variables Requested\n"
    "6,1,Calendar Year of Simulation[] ! When Annual Report Variables Requested\n"
    "7,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Hourly\n"
)

_VALID_BODY = (
    "End of Data Dictionary\n"
    "1,TEST ENV, 0.0, 0.0, 0.0, 0.0\n"
    "2,1, 1, 1, 0, 1, 0.00,60.00,Tuesday\n"
    "7,20.0\n"
    "End of Data\n"
)


class TestEsofileReaderErrors:
    def test_blank_line_in_header(self, tmp_path):
        eso = tmp_path / "blank_header.eso"
        eso.write_text(_HEADER + "\n")  # should trigger BlankLineError
        with pytest.raises(BlankLineError):
            process_eso_file(str(eso))

    def test_invalid_syntax_in_header(self, tmp_path):
        eso = tmp_path / "bad_header.eso"
        eso.write_text(_HEADER + "THIS IS NOT VALID SYNTAX AT ALL\n")  # no regex match
        with pytest.raises(InvalidLineSyntax):
            process_eso_file(str(eso))

    def test_blank_line_in_body(self, tmp_path):
        eso = tmp_path / "blank_body.eso"
        eso.write_text(
            _HEADER
            + "End of Data Dictionary\n"
            + "1,TEST ENV, 0.0, 0.0, 0.0, 0.0\n"
            + "\n"  # should trigger BlankLineError
        )
        with pytest.raises(BlankLineError):
            process_eso_file(str(eso))

    def test_incomplete_file(self, tmp_path):
        eso = tmp_path / "incomplete.eso"
        # File ends after the header without an 'End of Data' marker
        eso.write_text(_HEADER + "End of Data Dictionary\n")
        with pytest.raises(IncompleteFile, match="not complete"):
            process_eso_file(str(eso))

    def test_valid_minimal_file_parses(self, tmp_path):
        eso = tmp_path / "valid.eso"
        eso.write_text(_HEADER + _VALID_BODY)
        result = process_eso_file(str(eso))
        assert len(result) == 1
        assert result[0].environment_name == "TEST ENV"


class TestScheduleReference:
    """Variables reported under a schedule carry a trailing schedule name in
    the dictionary line, e.g. '... [C] !Hourly,ON'. When the same variable is
    reported both with and without a schedule the two dictionary lines collapse
    to one Variable, but both ids still appear in the body. This used to raise
    KeyError (issue #19); every id must be registered in the output bins.
    """

    def test_schedule_suffix_is_parsed(self):
        from db_eplusout_reader.processing.esofile_reader import process_header_line

        line = "276,1,BLOCK1:ZONE1,Zone Mean Air Temperature [C] !Hourly,ON"
        line_id, key, type_, units, frequency = process_header_line(line)
        assert line_id == 276
        assert key == "BLOCK1:ZONE1"
        assert type_ == "Zone Mean Air Temperature"
        assert units == "C"
        assert frequency == "hourly"

    def test_duplicate_variable_with_and_without_schedule(self, tmp_path):
        # 275 (no schedule) and 276 (schedule 'ON') share the same Variable.
        header = _HEADER + (
            "275,1,BLOCK1:ZONE1,Zone Mean Air Temperature [C] !Hourly\n"
            "276,1,BLOCK1:ZONE1,Zone Mean Air Temperature [C] !Hourly,ON\n"
        )
        body = (
            "End of Data Dictionary\n"
            "1,TEST ENV, 0.0, 0.0, 0.0, 0.0\n"
            "2,1, 1, 1, 0, 1, 0.00,60.00,Tuesday\n"
            "7,20.0\n"
            "275,21.0\n"
            "276,22.0\n"
            "End of Data\n"
        )
        eso = tmp_path / "schedule.eso"
        eso.write_text(header + body)

        result = process_eso_file(str(eso))  # must not raise KeyError

        outputs = result[0].outputs["hourly"]
        assert outputs[275] == [21.0]
        assert outputs[276] == [22.0]
