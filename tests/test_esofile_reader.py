"""Tests for low-level ESO file parsing in esofile_reader module.

Covers error paths: BlankLineError for blank lines in header and body,
InvalidLineSyntax for unexpected header lines, and IncompleteFile when
the file is truncated before the 'End of Data' marker.
"""
import pytest

from db_eplusout_reader.exceptions import BlankLineError, IncompleteFile, InvalidLineSyntax
from db_eplusout_reader.processing.esofile_reader import process_eso_file

# Minimal valid ESO header shared across tests
_HEADER = """\
Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2020.11.10 11:31
1,5,Environment Title[],Latitude[deg],Longitude[deg],Time Zone[],Elevation[m]
2,8,Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],Hour[],StartMinute[],EndMinute[],DayType
3,5,Cumulative Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],DayType  ! When Daily Report Variables Requested
4,2,Cumulative Days of Simulation[],Month[]  ! When Monthly Report Variables Requested
5,1,Cumulative Days of Simulation[] ! When Run Period Report Variables Requested
6,1,Calendar Year of Simulation[] ! When Annual Report Variables Requested
7,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Hourly
"""

_VALID_BODY = """\
End of Data Dictionary
1,TEST ENV, 0.0, 0.0, 0.0, 0.0
2,1, 1, 1, 0, 1, 0.00,60.00,Tuesday
7,20.0
End of Data
"""


class TestEsofileReaderErrors:
    def test_blank_line_in_header(self, tmp_path):
        eso = tmp_path / "blank_header.eso"
        eso.write_text(
            "Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2020.11.10 11:31\n"
            "1,5,Environment Title[],Latitude[deg],Longitude[deg],Time Zone[],Elevation[m]\n"
            "2,8,Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],"
            "Hour[],StartMinute[],EndMinute[],DayType\n"
            "3,5,Cumulative Day of Simulation[],Month[],Day of Month[],"
            "DST Indicator[1=yes 0=no],DayType  ! When Daily Report Variables Requested\n"
            "4,2,Cumulative Days of Simulation[],Month[]  ! When Monthly Report Variables Requested\n"
            "5,1,Cumulative Days of Simulation[] ! When Run Period Report Variables Requested\n"
            "6,1,Calendar Year of Simulation[] ! When Annual Report Variables Requested\n"
            "\n"  # blank line inside header — should trigger BlankLineError
        )
        with pytest.raises(BlankLineError):
            process_eso_file(str(eso))

    def test_invalid_syntax_in_header(self, tmp_path):
        eso = tmp_path / "bad_header.eso"
        eso.write_text(
            "Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2020.11.10 11:31\n"
            "1,5,Environment Title[],Latitude[deg],Longitude[deg],Time Zone[],Elevation[m]\n"
            "2,8,Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],"
            "Hour[],StartMinute[],EndMinute[],DayType\n"
            "3,5,Cumulative Day of Simulation[],Month[],Day of Month[],"
            "DST Indicator[1=yes 0=no],DayType  ! When Daily Report Variables Requested\n"
            "4,2,Cumulative Days of Simulation[],Month[]  ! When Monthly Report Variables Requested\n"
            "5,1,Cumulative Days of Simulation[] ! When Run Period Report Variables Requested\n"
            "6,1,Calendar Year of Simulation[] ! When Annual Report Variables Requested\n"
            "THIS IS NOT VALID SYNTAX AT ALL\n"  # invalid — no regex match, not End of Data Dictionary
        )
        with pytest.raises(InvalidLineSyntax):
            process_eso_file(str(eso))

    def test_blank_line_in_body(self, tmp_path):
        eso = tmp_path / "blank_body.eso"
        eso.write_text(
            _HEADER
            + "End of Data Dictionary\n"
            + "1,TEST ENV, 0.0, 0.0, 0.0, 0.0\n"
            + "\n"  # blank line in body — should trigger BlankLineError
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
