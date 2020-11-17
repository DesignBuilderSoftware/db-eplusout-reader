import os
import unittest

from db_esofile_reader import DBEsoFile, DBEsoFileCollection
from db_esofile_reader.constants import *

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


class TestEsofileReader(unittest.TestCase):
    def test_process_eso_file(self):
        file = DBEsoFile.from_path(os.path.join(TEST_FILES_DIR, "eplusout.eso"))
        expected = [H, D, M, RP]
        self.assertListEqual(expected, file.frequencies)

    def test_process_eso_file_collection(self):
        files = DBEsoFileCollection.from_path(
            os.path.join(TEST_FILES_DIR, "eplusout.eso")
        )
        expected = ["UNTITLED (01-01:31-12)"]
        self.assertListEqual(expected, [f.environment_name for f in files])
