"""Tests for date/time utilities in the esofile_time module.

Covers: find_num_of_days_annual, the annual+runperiod branch in
get_num_of_days, check_year_increment, validate_year (LeapYearMismatch
and StartDayMismatch), is_leap_year_ts_to_d, seek_year (design day
shortcut, year-match search, ValueError when nothing matches), and the
convert_raw_date_data branch that uses a default year of 2002 for
monthly-only data.
"""
import pytest

from db_eplusout_reader.constants import A, M, RP
from db_eplusout_reader.exceptions import LeapYearMismatch, StartDayMismatch
from db_eplusout_reader.processing.esofile_time import (
    EsoTimestamp,
    check_year_increment,
    convert_raw_date_data,
    find_num_of_days_annual,
    get_num_of_days,
    is_leap_year_ts_to_d,
    seek_year,
    validate_year,
)


class TestFindNumOfDaysAnnual:
    def test_single_year(self):
        result = find_num_of_days_annual([365], [365])
        assert result == [365]

    def test_multiple_years(self):
        result = find_num_of_days_annual([365, 365], [730])
        assert result == [365, 365]

    def test_partial_year(self):
        result = find_num_of_days_annual([180], [180])
        assert result == [180]


class TestGetNumOfDaysAnnualBranch:
    def test_annual_and_rp_together(self):
        # When both A and RP keys are present, annual days should be
        # derived from the runperiod total.
        cumulative_days = {
            M: [31, 59, 90, 121, 151, 182, 212, 243, 273, 304, 334, 365],
            A: [365],
            RP: [365],
        }
        result = get_num_of_days(cumulative_days)
        assert result[A] == [365]
        assert result[RP] == [365]

    def test_without_annual(self):
        cumulative_days = {
            M: [31, 59],
            RP: [59],
        }
        result = get_num_of_days(cumulative_days)
        assert A not in result
        assert result[RP] == [59]


class TestCheckYearIncrement:
    def test_same_object_returns_false(self):
        ts = EsoTimestamp(1, 1, 0, 0)
        assert check_year_increment(ts, ts) is False

    def test_later_step_no_increment(self):
        ts1 = EsoTimestamp(1, 1, 0, 0)
        ts2 = EsoTimestamp(6, 15, 0, 0)
        assert check_year_increment(ts1, ts2) is False

    def test_same_month_day_no_increment(self):
        ts1 = EsoTimestamp(3, 15, 0, 0)
        ts2 = EsoTimestamp(3, 15, 0, 0)
        # Different objects but equal values: first >= current is True
        assert check_year_increment(ts1, ts2) is True

    def test_year_boundary_returns_true(self):
        ts_dec = EsoTimestamp(12, 31, 0, 0)
        ts_jan = EsoTimestamp(1, 1, 0, 0)
        assert check_year_increment(ts_dec, ts_jan) is True


class TestValidateYear:
    def test_leap_year_mismatch_standard_year_for_leap_data(self):
        # Data is a leap year (is_leap=True) but 2019 is not a leap year
        date = EsoTimestamp(2, 28, 0, 0)
        with pytest.raises(LeapYearMismatch):
            validate_year(2019, True, date, "Thursday")

    def test_leap_year_mismatch_leap_year_for_standard_data(self):
        # Data is standard (is_leap=False) but 2020 is a leap year
        date = EsoTimestamp(1, 1, 0, 0)
        with pytest.raises(LeapYearMismatch):
            validate_year(2020, False, date, "Wednesday")

    def test_start_day_mismatch(self):
        # Jan 1 2019 is a Tuesday, not Monday
        date = EsoTimestamp(1, 1, 0, 0)
        with pytest.raises(StartDayMismatch):
            validate_year(2019, False, date, "Monday")

    def test_summer_design_day_passes(self):
        # Design-day names should bypass day-of-week checking
        date = EsoTimestamp(7, 21, 0, 0)
        validate_year(2019, False, date, "SummerDesignDay")  # no exception

    def test_winter_design_day_passes(self):
        date = EsoTimestamp(1, 21, 0, 0)
        validate_year(2019, False, date, "WinterDesignDay")  # no exception

    def test_correct_year_and_day_passes(self):
        # Jan 1, 2019 is a Tuesday
        date = EsoTimestamp(1, 1, 0, 0)
        validate_year(2019, False, date, "Tuesday")  # no exception


class TestIsLeapYearTsToD:
    def test_with_feb29_returns_true(self):
        dates = [
            EsoTimestamp(1, 1, 0, 0),
            EsoTimestamp(2, 28, 0, 0),
            EsoTimestamp(2, 29, 0, 0),
            EsoTimestamp(3, 1, 0, 0),
        ]
        assert is_leap_year_ts_to_d(dates) is True

    def test_without_feb29_returns_false(self):
        dates = [
            EsoTimestamp(1, 1, 0, 0),
            EsoTimestamp(2, 28, 0, 0),
            EsoTimestamp(3, 1, 0, 0),
        ]
        assert is_leap_year_ts_to_d(dates) is False

    def test_single_entry_returns_false(self):
        dates = [EsoTimestamp(6, 15, 0, 0)]
        assert is_leap_year_ts_to_d(dates) is False


class TestSeekYear:
    def test_summer_design_day_returns_2002(self):
        date = EsoTimestamp(7, 21, 0, 0)
        year = seek_year(False, date, "SummerDesignDay", 2020)
        assert year == 2002

    def test_winter_design_day_returns_2002(self):
        date = EsoTimestamp(1, 21, 0, 0)
        year = seek_year(False, date, "WinterDesignDay", 2020)
        assert year == 2002

    def test_finds_matching_year(self):
        # Jan 1, 2019 is a Tuesday; seek_year should find 2019
        date = EsoTimestamp(1, 1, 0, 0)
        year = seek_year(False, date, "Tuesday", 2020)
        assert year == 2019

    def test_no_match_raises_value_error(self):
        date = EsoTimestamp(1, 1, 0, 0)
        with pytest.raises(ValueError, match="Failed to automatically find year"):
            seek_year(False, date, "NotADay", 5)


class TestConvertRawDateDataDefaultYear:
    def test_monthly_only_defaults_to_2002(self):
        # When no TS/H/D data is present, year defaults to 2002
        raw_dates = {M: [EsoTimestamp(1, 1, 0, 0), EsoTimestamp(2, 1, 0, 0)]}
        days_of_week = {M: ["Tuesday", "Friday"]}
        dates = convert_raw_date_data(raw_dates, days_of_week, year=None)
        assert dates[M][0].year == 2002

    def test_monthly_only_with_explicit_year(self):
        raw_dates = {M: [EsoTimestamp(1, 1, 0, 0)]}
        days_of_week = {M: ["Tuesday"]}
        dates = convert_raw_date_data(raw_dates, days_of_week, year=2015)
        assert dates[M][0].year == 2015
