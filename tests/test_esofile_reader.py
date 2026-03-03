"""Tests for low-level ESO file parsing in esofile_reader module.

Covers error paths: BlankLineError for blank lines in header and body,
InvalidLineSyntax for unexpected header lines, and IncompleteFile when
the file is truncated before the 'End of Data' marker.
"""
from pathlib import Path

import pytest

from db_eplusout_reader.exceptions import BlankLineError, IncompleteFile, InvalidLineSyntax
from db_eplusout_reader.processing.esofile_reader import process_eso_file

_TEST_FILES = Path(__file__).parent / "test_files"

# Minimal valid ESO header read from a fixture file; long lines live there,
# not in Python source.
_HEADER = (_TEST_FILES / "minimal_header.eso").read_text()

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
        eso.write_text(
            _HEADER
            + "\n"  # blank line inside header — should trigger BlankLineError
        )
        with pytest.raises(BlankLineError):
            process_eso_file(str(eso))

    def test_invalid_syntax_in_header(self, tmp_path):
        eso = tmp_path / "bad_header.eso"
        eso.write_text(
            _HEADER
            + "THIS IS NOT VALID SYNTAX AT ALL\n"  # no regex match
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
