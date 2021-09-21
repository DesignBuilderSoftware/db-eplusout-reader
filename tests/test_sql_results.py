import os
import unittest
from datetime import datetime

from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import RP, D, H, M
from db_eplusout_reader.sql_reader import get_timestamps_from_sql

SQL_PATH = os.path.join(os.path.dirname(__file__), "test_files", "eplusout.sql")


class TestSql(unittest.TestCase):
    def test_get_results_exact_match(self):
        variable = Variable(
            "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""
        )
        results = get_results(SQL_PATH, variable, frequency=H)
        self.assertListEqual(list(results.keys()), [variable])
        self.assertEqual(8760, len(results[variable]))

    def test_get_results_multiple_variables(self):
        variables = [
            Variable("BLOCK1:ZONE2", "Zone Air Relative Humidity", "%"),
            Variable(
                "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""
            ),
        ]
        results = get_results(SQL_PATH, variables, frequency=D)
        self.assertListEqual(list(results.keys()), variables)
        self.assertTrue(all(map(lambda x: len(x) == 365, results.values())))

    def test_get_results_alike(self):
        variable = Variable("PEOPLE BLOCK", "Zone Thermal Comfort Fanger Model", "")
        results = get_results(SQL_PATH, variable, frequency=H, alike=True)
        expected = [
            Variable(
                "PEOPLE BLOCK1:ZONE1", "Zone Thermal Comfort Fanger Model PMV", ""
            ),
            Variable(
                "PEOPLE BLOCK1:ZONE1", "Zone Thermal Comfort Fanger Model PPD", "%"
            ),
            Variable(
                "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""
            ),
            Variable(
                "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PPD", "%"
            ),
        ]
        self.assertListEqual(expected, list(results.keys()))

    def test_get_all_results(self):
        variable = Variable(None, None, None)
        results = get_results(SQL_PATH, variable, H, alike=True)
        self.assertEqual(35, len(results.keys()))

    def test_get_all_sliced_results(self):
        variable = Variable(None, None, None)
        results = get_results(
            SQL_PATH,
            variable,
            frequency=H,
            alike=False,
            start_date=datetime(2013, 1, 1),
            end_date=datetime(2013, 2, 1),
        )
        self.assertEqual(35, len(results.keys()))
        self.assertEqual(31 * 24, len(results.first_array))

    def test_get_results_start_end_dates(self):
        variable = Variable(
            "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PPD", "%"
        )
        results = get_results(
            SQL_PATH,
            variables=variable,
            frequency=H,
            alike=False,
            start_date=datetime(2013, 5, 31, 0),
            end_date=datetime(2013, 5, 31, 23, 59),
        )
        self.assertEqual(24, len(list(results.values())[0]))

    def test_get_timestamps_monthly(self):
        timestamps = get_timestamps_from_sql(SQL_PATH, "monthly")
        expected = [datetime(2013, i, 1) for i in range(1, 13)]
        self.assertListEqual(expected, timestamps)

    def test_get_results_meter(self):
        variable = Variable("", "DistrictHeating:Facility", "J")
        results = get_results(SQL_PATH, variables=variable, frequency=RP)
        self.assertDictEqual({variable: [30475176136.970848]}, results)

    def test_results_time_series(self):
        for frequency, expected in zip([RP, M, D, H], [1, 12, 365, 8760]):
            results_dictionary = get_results(
                SQL_PATH,
                Variable("", "DistrictHeating:Facility", "J"),
                frequency=frequency,
            )
            self.assertEqual(expected, len(results_dictionary.time_series))

    def test_results_to_csv(self):
        self.assertTrue(False)
