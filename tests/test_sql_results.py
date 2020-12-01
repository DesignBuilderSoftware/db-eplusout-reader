import os
import unittest
from datetime import datetime

from db_esofile_reader import Variable, get_results
from db_esofile_reader.constants import *
from db_esofile_reader.sql_reader import get_timestamps_from_sql

SQL_PATH = os.path.join(os.path.dirname(__file__), "test_files", "eplusout.sql")


class TestSql(unittest.TestCase):
    def test_get_results_exact_match(self):
        variable = Variable(
            H, "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""
        )
        results = get_results(SQL_PATH, variable)
        self.assertListEqual(list(results.keys()), [variable])
        self.assertEqual(8760, len(results[variable]))

    def test_get_results_multiple_variables(self):
        variables = [
            Variable(D, "BLOCK1:ZONE2", "Zone Air Relative Humidity", "%"),
            Variable(D, "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
        ]
        results = get_results(SQL_PATH, variables)
        self.assertListEqual(list(results.keys()), variables)
        self.assertTrue(all(map(lambda x: len(x) == 365, results.values())))

    def test_get_results_alike(self):
        variable = Variable(
            "hourly", "PEOPLE BLOCK", "Zone Thermal Comfort Fanger Model", ""
        )
        results = get_results(SQL_PATH, variable, alike=True)
        expected = [
            Variable(H, 'PEOPLE BLOCK1:ZONE1', 'Zone Thermal Comfort Fanger Model PMV', ''),
            Variable(H, 'PEOPLE BLOCK1:ZONE1', 'Zone Thermal Comfort Fanger Model PPD', '%'),
            Variable(H, 'PEOPLE BLOCK1:ZONE2', 'Zone Thermal Comfort Fanger Model PMV', ''),
            Variable(H, 'PEOPLE BLOCK1:ZONE2', 'Zone Thermal Comfort Fanger Model PPD', '%'),
        ]
        self.assertListEqual(expected, list(results.keys()))

    def test_get_all_results(self):
        variable = Variable(None, None, None, None)
        results = get_results(SQL_PATH, variable, alike=True)
        self.assertEqual(140, len(results.keys()))

    def test_get_all_sliced_results(self):
        variable = Variable(None, None, None, None)
        results = get_results(
            SQL_PATH,
            variable,
            alike=True,
            start_date=datetime(2013, 1, 1),
            end_date=datetime(2013, 2, 1)
        )
        self.assertEqual(140, len(results.keys()))

    def test_get_results_start_end_dates(self):
        variable = Variable(
            H, "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PPD", "%"
        ),
        results = get_results(
            SQL_PATH,
            variables=variable,
            alike=False,
            start_date=datetime(2013, 5, 31, 0),
            end_date=datetime(2013, 5, 31, 23, 59)
        )
        self.assertEqual(24, len(list(results.values())[0]))

    def test_get_timestamps_monthly(self):
        timestamps = get_timestamps_from_sql(SQL_PATH, "monthly")
        expected = [datetime(2013, i, 1) for i in range(1, 13)]
        self.assertListEqual(expected, timestamps)

    def test_get_results_meter(self):
        variable = Variable(RP, "", "DistrictHeating:Facility", "J")
        results = get_results(SQL_PATH, variables=variable)
        self.assertDictEqual({variable: [30475176136.970848]}, results)
