"""Cross-version ESO and SQL smoke tests.

Each test runs once per versioned file in test_files/ via the
``any_eso_file`` / ``any_eso_path`` / ``any_sql_path`` fixtures.
"""

from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import D, H, M


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
