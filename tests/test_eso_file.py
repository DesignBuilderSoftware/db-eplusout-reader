import os

from db_eplusout_reader.constants import RP, D, H, M

ESO_PATH = os.path.join(os.path.dirname(__file__), "test_files", "eplusout.eso")


class TestEsofileReader:
    def test_process_eso_file(self, session_eso_file):
        assert session_eso_file.frequencies == [H, D, M, RP]

    def test_process_eso_file_collection(self, session_eso_file_collection):
        assert [f.environment_name for f in session_eso_file_collection] == [
            "UNTITLED (01-01:31-12)"
        ]
