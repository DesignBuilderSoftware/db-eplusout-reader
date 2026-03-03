import os
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from db_eplusout_reader import DBEsoFile, DBEsoFileCollection, Variable
from db_eplusout_reader.constants import H
from db_eplusout_reader.results_dict import ResultsDictionary

TEST_FILES_DIR = Path(__file__).parent / "test_files"

# Versioned file stems present in test_files/
ESO_STEMS = [
    "920_eplusout",
    "231_1ZoneUncontrolled",
    "251_1ZoneUncontrolled",
    "252_1ZoneUncontrolled",
]
SQL_STEMS = ESO_STEMS


@pytest.fixture(scope="function")
def temp_csv(tmp_path):
    try:
        yield os.path.join(str(tmp_path), "test.csv")
    finally:
        shutil.rmtree(str(tmp_path), ignore_errors=True)


@pytest.fixture(scope="session")
def test_files_dir():
    return str(TEST_FILES_DIR.parent)


# ---------------------------------------------------------------------------
# Single-file fixtures used by tests that rely on specific variables in the
# 920 multi-zone model
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sql_path():
    return str(TEST_FILES_DIR / "920_eplusout.sql")


@pytest.fixture(scope="session")
def eso_path():
    return str(TEST_FILES_DIR / "920_eplusout.eso")


@pytest.fixture(scope="session")
def session_eso_file(eso_path):
    return DBEsoFile.from_path(eso_path)


@pytest.fixture(scope="session")
def session_eso_file_collection(eso_path):
    return DBEsoFileCollection.from_path(eso_path)


# ---------------------------------------------------------------------------
# Parameterized fixtures — one test instance per versioned ESO file.
# Yields the run-period DBEsoFile extracted from the collection (or the
# file directly when it contains only one environment).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", params=ESO_STEMS)
def any_eso_path(request):
    return str(TEST_FILES_DIR / f"{request.param}.eso")


@pytest.fixture(scope="session")
def any_eso_file(any_eso_path):
    """The run-period DBEsoFile for each versioned ESO, regardless of whether
    the file contains a single environment or a collection."""
    try:
        return DBEsoFile.from_path(any_eso_path)
    except Exception:
        col = DBEsoFileCollection.from_path(any_eso_path)
        run_period = next(f for f in col if "RUN PERIOD" in f.environment_name.upper())
        return run_period


# ---------------------------------------------------------------------------
# Parameterized SQL path fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", params=SQL_STEMS)
def any_sql_path(request):
    return str(TEST_FILES_DIR / f"{request.param}.sql")


# ---------------------------------------------------------------------------
# Misc fixtures
# ---------------------------------------------------------------------------


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
