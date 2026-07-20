"""Tests for the ResultsWriter csv output helper.

Covers writer keyword arguments and the legacy (non Python 3) binary-mode
open branch which is otherwise unreachable on a modern interpreter.
"""

import os
import sys

from db_eplusout_reader.results_dict import ResultsWriter


class TestWriteTableToCsv:
    def test_custom_delimiter(self, tmp_path):
        path = str(tmp_path / "out.csv")
        table = [["a", "b"], [1, 2]]
        ResultsWriter.write_table_to_csv(table, path, ";", False, "")
        with open(path) as f:
            content = f.read()
        assert content.splitlines() == ["a;b", "1;2"]

    def test_title_row_written_first(self, tmp_path):
        path = str(tmp_path / "out.csv")
        ResultsWriter.write_table_to_csv([["a"]], path, ",", False, "My Title")
        with open(path) as f:
            lines = f.read().splitlines()
        assert lines == ["My Title", "a"]

    def test_append_mode_keeps_existing_rows(self, tmp_path):
        path = str(tmp_path / "out.csv")
        ResultsWriter.write_table_to_csv([["first"]], path, ",", False, "")
        ResultsWriter.write_table_to_csv([["second"]], path, ",", True, "")
        with open(path) as f:
            lines = f.read().splitlines()
        assert lines == ["first", "second"]

    def test_legacy_python2_open_kwargs_branch(self, tmp_path, monkeypatch):
        # Simulate a non Python 3 interpreter so the binary-mode branch runs.
        # An empty table with no title never calls writer.writerow, so the
        # binary file handle is never written to and stays valid.
        monkeypatch.setattr(sys, "version_info", (2, 7, 18))
        path = str(tmp_path / "legacy.csv")
        ResultsWriter.write_table_to_csv([], path, ",", False, "")
        assert os.path.exists(path)
        assert os.path.getsize(path) == 0
