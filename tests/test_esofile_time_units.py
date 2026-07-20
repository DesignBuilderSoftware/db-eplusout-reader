"""Unit tests for date and time helpers in the esofile_time module.

Complements test_esofile_time.py with checks for datetime generation over
year boundaries, cumulative days handling when no monthly+ data exists,
leap year detection over multi year arrays, timestamp parsing edge cases
and 'convert_raw_date_data' with an explicitly supplied year.
"""

from datetime import datetime

import pytest

from db_eplusout_reader.constants import RP, TS, A, D, H, M
from db_eplusout_reader.exceptions import StartDayMismatch
from db_eplusout_reader.processing.esofile_time import (
    EsoTimestamp,
    convert_raw_date_data,
    generate_datetime_dates,
    get_allowed_years,
    get_lowest_frequency,
    get_n_days_from_cumulative,
    is_leap_year_ts_to_d,
    parse_eso_timestamp,
    update_start_dates,
)


class TestParseEsoTimestamp:
    def test_midnight_rollover(self):
        # 24:60 rolls over to midnight of the next day
        assert parse_eso_timestamp(2002, 12, 31, 24, 60) == datetime(2003, 1, 1, 0, 0)

    def test_end_of_hour(self):
        assert parse_eso_timestamp(2002, 1, 1, 5, 60) == datetime(2002, 1, 1, 5, 0)

    def test_hour_zero(self):
        assert parse_eso_timestamp(2002, 1, 1, 0, 30) == datetime(2002, 1, 1, 0, 30)

    def test_regular_timestep(self):
        assert parse_eso_timestamp(2002, 6, 15, 10, 30) == datetime(2002, 6, 15, 9, 30)


class TestGenerateDatetimeDates:
    def test_single_year(self):
        raw = [EsoTimestamp(1, 1, 0, 0), EsoTimestamp(6, 1, 0, 0)]
        assert generate_datetime_dates(raw, 2002) == [
            datetime(2002, 1, 1),
            datetime(2002, 6, 1),
        ]

    def test_year_increments_on_rollover(self):
        raw = [
            EsoTimestamp(6, 1, 0, 0),
            EsoTimestamp(12, 1, 0, 0),
            EsoTimestamp(1, 1, 0, 0),
        ]
        assert generate_datetime_dates(raw, 2002) == [
            datetime(2002, 6, 1),
            datetime(2002, 12, 1),
            datetime(2003, 1, 1),
        ]


class TestUpdateStartDates:
    def test_monthly_start_date_updated_from_hourly(self):
        # a partial-year run starting 2 January: the monthly and runperiod
        # start dates are replaced with the (zeroed) first sub-monthly date
        dates = {
            H: [datetime(2002, 1, 2, 5, 30), datetime(2002, 1, 2, 6, 30)],
            M: [datetime(2002, 1, 1)],
            RP: [datetime(2002, 1, 1)],
        }
        updated = update_start_dates(dates)
        assert updated[M][0] == datetime(2002, 1, 2)
        assert updated[RP][0] == datetime(2002, 1, 2)
        # sub-monthly dates themselves are untouched
        assert updated[H][0] == datetime(2002, 1, 2, 5, 30)

    def test_annual_and_runperiod_only_left_unchanged(self):
        # without any timestep to monthly data there is no reference
        # to update from, so dates pass through unchanged
        dates = {A: [datetime(2002, 1, 1)], RP: [datetime(2002, 1, 1)]}
        updated = update_start_dates(dates)
        assert updated == {A: [datetime(2002, 1, 1)], RP: [datetime(2002, 1, 1)]}


class TestGetNDaysFromCumulative:
    def test_empty_returns_none(self):
        assert get_n_days_from_cumulative({}) is None

    def test_monthly_cumulative_converted(self):
        n_days = get_n_days_from_cumulative({M: [31, 59, 90]})
        assert n_days == {M: [31, 28, 31]}


class TestIsLeapYearTsToD:
    def test_stops_at_year_rollover(self):
        # no 29 February before the year increments -> not a leap year
        raw = [
            EsoTimestamp(1, 1, 0, 0),
            EsoTimestamp(2, 28, 0, 0),
            EsoTimestamp(1, 1, 0, 0),  # rollover into second year
            EsoTimestamp(2, 29, 0, 0),  # leap day in second year is ignored
        ]
        assert is_leap_year_ts_to_d(raw) is False

    def test_detects_leap_day(self):
        raw = [EsoTimestamp(2, 28, 0, 0), EsoTimestamp(2, 29, 0, 0)]
        assert is_leap_year_ts_to_d(raw) is True


class TestGetLowestFrequency:
    def test_timestep_wins(self):
        assert get_lowest_frequency([RP, M, TS, H]) == TS

    def test_monthly_and_up(self):
        assert get_lowest_frequency([RP, A, M]) == M


class TestGetAllowedYears:
    def test_returns_requested_number_of_samples(self):
        years = get_allowed_years(False, EsoTimestamp(1, 1, 0, 0), "Tuesday", 2020, 3)
        assert len(years) == 3
        assert years == sorted(years, reverse=True)
        for year in years:
            assert datetime(year, 1, 1).strftime("%A") == "Tuesday"


class TestConvertRawDateDataWithExplicitYear:
    def test_valid_explicit_year(self):
        # 1 January 2019 is a Tuesday in a non-leap year
        raw_dates = {H: [EsoTimestamp(1, 1, 1, 60)], D: [EsoTimestamp(1, 1, 0, 0)]}
        days_of_week = {H: ["Tuesday"], D: ["Tuesday"]}
        dates = convert_raw_date_data(raw_dates, days_of_week, 2019)
        assert dates[H] == [datetime(2019, 1, 1, 1)]
        assert dates[D] == [datetime(2019, 1, 1)]

    def test_invalid_explicit_year_raises(self):
        # 1 January 2018 is a Monday, not a Tuesday
        raw_dates = {H: [EsoTimestamp(1, 1, 1, 60)]}
        days_of_week = {H: ["Tuesday"]}
        with pytest.raises(StartDayMismatch):
            convert_raw_date_data(raw_dates, days_of_week, 2018)

    def test_year_sought_automatically_when_none(self):
        raw_dates = {H: [EsoTimestamp(1, 1, 1, 60)]}
        days_of_week = {H: ["Tuesday"]}
        dates = convert_raw_date_data(raw_dates, days_of_week, None)
        assert dates[H] == [datetime(2019, 1, 1, 1)]
