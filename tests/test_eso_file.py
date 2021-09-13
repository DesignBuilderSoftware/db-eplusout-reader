import os
import unittest

from db_eplusout_reader import DBEsoFile, DBEsoFileCollection
from db_eplusout_reader.constants import D, H, M, RP

ESO_PATH = os.path.join(os.path.dirname(__file__), "test_files", "eplusout.eso")


class TestEsofileReader(unittest.TestCase):
    def test_process_eso_file(self):
        file = DBEsoFile.from_path(ESO_PATH)
        expected = [H, D, M, RP]
        self.assertListEqual(expected, file.frequencies)

    def test_process_eso_file_collection(self):
        files = DBEsoFileCollection.from_path(ESO_PATH)
        expected = ["UNTITLED (01-01:31-12)"]
        self.assertListEqual(expected, [f.environment_name for f in files])
