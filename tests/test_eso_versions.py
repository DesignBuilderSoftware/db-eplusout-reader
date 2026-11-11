"""Cross-version ESO and SQL smoke tests.

Each test runs once per versioned file in test_files/ via the
``any_eso_file`` / ``any_eso_path`` / ``any_sql_path`` fixtures.
"""

from datetime import datetime

import pytest

from db_eplusout_reader import DBEsoFileCollection, Variable, get_results
from db_eplusout_reader.constants import RP, TS, A, D, H, M

from .conftest import TEST_FILES_DIR


class TestEsoAcrossVersions:
    def test_get_results_hourly(self, any_eso_file):
        variables = [Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")]
        results = any_eso_file.get_results(variables, H)
        assert len(results) == 1
        assert len(results.first_array) == 8760

    def test_get_results_daily(self, any_eso_file):
        variables = [Variable(None, None, None)]
        results = any_eso_file.get_results(variables, D)
        assert len(results.time_series) == 365

    def test_get_results_monthly(self, any_eso_file):
        variables = [Variable(None, None, None)]
        results = any_eso_file.get_results(variables, M)
        assert len(results.time_series) == 12

    def test_frequencies(self, any_eso_file):
        # Raised KeyError: '' for EnergyPlus 10.0+ files before issue #32 was fixed.
        assert any_eso_file.frequencies == [TS, H, D, M, RP]


class TestAnnualOutputs:
    """EnergyPlus 26.2 file with an !Annual variable (issue #32).

    Generated with EnergyPlus 26.2 from resources/252_1ZoneUncontrolledAnnualOutputs.idf
    after the 25.2 -> 26.1 -> 26.2 transitions (which only change the Version
    object) and the Chicago TMY3 weather file in resources/. The model runs two
    design days and a 2018-2019 run period.
    """

    _VARIABLE = Variable("ZONE ONE", "Zone Mean Air Temperature", "C")

    @pytest.fixture(scope="class")
    def collection(self):
        path = TEST_FILES_DIR / "262_1ZoneUncontrolledAnnualOutputs.eso"
        return DBEsoFileCollection.from_path(str(path))

    @pytest.fixture(scope="class")
    def run_period(self, collection):
        return next(f for f in collection if "RUN PERIOD" in f.environment_name.upper())

    def test_frequencies(self, run_period):
        assert run_period.frequencies == [D, A, RP]

    def test_annual_results(self, run_period):
        results = run_period.get_results(self._VARIABLE, A)
        assert results.time_series == [datetime(2018, 1, 1), datetime(2019, 1, 1)]
        assert len(results.first_array) == 2
        assert run_period.n_days[A] == [365, 365]

    def test_design_days_have_no_annual_rows(self, collection):
        design_days = [f for f in collection if "RUN PERIOD" not in f.environment_name.upper()]
        assert len(design_days) == 2
        for eso_file in design_days:
            assert eso_file.n_days[A] == []


class TestSqlAcrossVersions:
    def test_get_results_hourly(self, any_sql_path):
        variable = Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")
        results = get_results(any_sql_path, variable, frequency=H)
        assert len(results) == 1
        # 8760 for run-period-only files; 8808 when design days are included
        assert len(results.first_array) in {8760, 8808}

    def test_get_results_monthly(self, any_sql_path):
        variable = Variable(None, None, None)
        results = get_results(any_sql_path, variable, frequency=M)
        # 12 for run-period-only files; 14 when design days are included
        assert len(results.time_series) in {12, 14}
