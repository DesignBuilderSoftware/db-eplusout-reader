import os
import shutil
from datetime import datetime

import pytest

from db_eplusout_reader import DBEsoFile, DBEsoFileCollection, Variable
from db_eplusout_reader.constants import H
from db_eplusout_reader.results_dict import ResultsDictionary


@pytest.fixture(scope="function")
def temp_csv(tmp_path):
    try:
        yield os.path.join(str(tmp_path), "test.csv")
    finally:
        shutil.rmtree(str(tmp_path), ignore_errors=True)


@pytest.fixture(scope="session")
def test_files_dir():
    return os.path.dirname(__file__)


@pytest.fixture(scope="session")
def sql_path(test_files_dir):
    return os.path.join(test_files_dir, "test_files", "eplusout.sql")


@pytest.fixture(scope="session")
def eso_path(test_files_dir):
    return os.path.join(test_files_dir, "test_files", "eplusout.eso")


@pytest.fixture(scope="session")
def session_eso_file(eso_path):
    return DBEsoFile.from_path(eso_path)


@pytest.fixture(scope="session")
def session_eso_file_collection(eso_path):
    return DBEsoFileCollection.from_path(eso_path)


@pytest.fixture(scope="function")
def results_dictionary():
    rd = ResultsDictionary(frequency=H)
    rd.time_series = [
        datetime(2002, 1, 1, 0),
        datetime(2002, 1, 2, 0),
        datetime(2002, 1, 3, 0),
    ]
    rd[Variable("Temperature", "Zone2", "C")] = [22, 23, 19]
    rd[Variable("Temperature", "Zone1", "C")] = [20, 21, 20]
    rd[Variable("Temperature", "Zone3", "C")] = [19, 23, 20]
    return rd
