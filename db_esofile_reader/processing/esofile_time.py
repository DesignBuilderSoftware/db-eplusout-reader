import calendar
import logging
from collections import namedtuple
from datetime import datetime, timedelta

from db_esofile_reader.constants import *
from db_esofile_reader.exceptions import LeapYearMismatch, StartDayMismatch

EsoTimestamp = namedtuple("EsoTimestamp", "month day hour end_minute")


def parse_eso_timestamp(year, month, day, hour, end_minute):
    """
    Convert E+ time format to format acceptable by datetime module.

    EnergyPlus date and time format is not compatible with
    datetime.datetime module. This because hourly information
    can be '24' and end minute can be '60' - which is not
    allowed.

    To get around the issue, logic is in place to
    convert raw input into format as required for datetime
    (or datetime like) module.
    """

    if hour == 24 and end_minute == 60:
        shifted_datetime = datetime(year, month, day, hour - 1)
        corrected_datetime = shifted_datetime + timedelta(hours=1)
    elif end_minute == 60:
        # Convert last timestep of an hour
        corrected_datetime = datetime(year, month, day, hour, 0)
    elif hour == 0:
        corrected_datetime = datetime(year, month, day, hour, end_minute)
    else:
        corrected_datetime = datetime(year, month, day, hour - 1, end_minute)
    return corrected_datetime


def get_month_n_days_from_cumulative(monthly_cumulative_days):
    """
    Transform consecutive number of days in monthly data to actual number of days.

    EnergyPlus monthly results report a total consecutive number of days for each day.
    Raw data reports table as 31, 59..., this function calculates and returns
    actual number of days for each month 31, 28...
    """
    old_num = monthly_cumulative_days.pop(0)
    m_actual_days = [old_num]
    for num in monthly_cumulative_days:
        new_num = num - old_num
        m_actual_days.append(new_num)
        old_num += new_num
    return m_actual_days


def find_num_of_days_annual(ann_num_of_days, rp_num_of_days):
    """ Use runperiod data to calculate number of days for each annual period. """
    days = rp_num_of_days[0] // len(ann_num_of_days)
    return [days for _ in ann_num_of_days]


def get_num_of_days(cumulative_days):
    """ Split num of days and date. """
    num_of_days = {}
    for table, values in cumulative_days.items():
        if table == M:
            # calculate actual number of days for monthly table
            num_of_days[M] = get_month_n_days_from_cumulative(values)
        else:
            num_of_days[table] = values
    # calculate number of days for annual table for
    # an incomplete year run or multi year analysis
    if A in cumulative_days.keys() and RP in cumulative_days.keys():
        num_of_days[A] = find_num_of_days_annual(num_of_days[A], num_of_days[RP])
    return num_of_days


def check_year_increment(first_step_data, current_step_data):
    """ Check if year value should be incremented inside environment table. """
    if first_step_data is current_step_data:
        # do not increment first step
        return False
    elif first_step_data >= current_step_data:
        # duplicate date -> increment year
        return True
    else:
        return False


def generate_datetime_dates(raw_dates, year):
    """ Generate datetime index for a given period. """
    dates = []
    for i in range(0, len(raw_dates)):
        # based on the first, current and previous
        # steps decide if the year should be incremented
        if check_year_increment(raw_dates[0], raw_dates[i]):
            year += 1
        # year can be incremented automatically when converting to datetime
        date = parse_eso_timestamp(year, *raw_dates[i])
        dates.append(date)
    return dates


def update_start_dates(dates):
    """ Set accurate first date for monthly+ tables. """

    def set_start_date(orig, refs):
        for ref in refs.values():
            orig[0] = ref[0].replace(hour=0, minute=0)
            return orig

    timestep_to_monthly_dates = {k: dates[k] for k in dates if k in [TS, H, D, M]}
    if timestep_to_monthly_dates:
        for frequency in (M, A, RP):
            if frequency in dates:
                dates[frequency] = set_start_date(dates[frequency], timestep_to_monthly_dates)
    return dates


def get_n_days_from_cumulative(cumulative_days):
    """ Convert cumulative days to number of days pers step. """
    if cumulative_days:
        # Separate number of days data if any M to RP table is available
        num_of_days = get_num_of_days(cumulative_days)
    else:
        num_of_days = None
    return num_of_days


def validate_year(year, is_leap, date, day):
    """ Check if date for given and day corresponds to specified year. """
    if calendar.isleap(year) is is_leap:
        test_datetime = datetime(year, date.month, date.day)
        test_day = test_datetime.strftime("%A")
        if day != test_day and day not in ("SummerDesignDay", "WinterDesignDay",):
            max_year = datetime.now().year + 10  # give some choices from future
            suitable_years = get_allowed_years(is_leap, date, day, max_year, n_samples=3)
            formatted_day = test_datetime.strftime('%Y-%m-%d')
            raise StartDayMismatch(
                "Start day '{}' for given day '{}'"
                " does not correspond to real calendar day '{}'!"
                "\nEither set 'year' kwarg as 'None' to identify year automatically"
                " or use one of '{}'.".format(day, formatted_day, test_day, suitable_years)
            )
    else:
        raise LeapYearMismatch(
            "Specified year '{0}' does not match expected calendar data!"
            " Outputs are reported for {1} year"
            " but given year '{0}' is {2}."
            " Either set 'year' kwarg as 'None' to seek year automatically"
            " or use {1} year.".format(
                year, 'leap' if is_leap else 'standard', 'standard' if is_leap else 'leap'
            )
        )


def is_leap_year_ts_to_d(raw_dates_arr):
    """ Check if first year is leap based on timestep, hourly or daily data. """
    for tup in raw_dates_arr:
        if (tup.month, tup.day) == (2, 29):
            return True
        elif check_year_increment(raw_dates_arr[0], tup):
            # stop once first year is covered
            return False
    else:
        return False


def seek_year(is_leap, date, day, max_year):
    """ Find first year matching given criteria. """
    for year in range(max_year, 0, -1):
        if day in ("SummerDesignDay", "WinterDesignDay"):
            logging.info("Sizing simulation, setting year to 2002.")
            year = 2002
            break
        elif calendar.isleap(year) is is_leap:
            test_datetime = datetime(year, date.month, date.day)
            test_start_day = test_datetime.strftime("%A")
            if day == test_start_day:
                break
    else:
        raise ValueError(
            "Failed to automatically find year for following arguments"
            " is_leap='{}', date='{}' and day='{}'."
            " It seems that there ins't a year between 0 - {} matching"
            " date and day of week combination.".format(is_leap, date, day, max_year)
        )
    return year


def get_allowed_years(
    is_leap, first_date, first_day, max_year, n_samples=4,
):
    """ Get a sample of allowed years for given conditions. """
    allowed_years = []
    for i in range(n_samples):
        year = seek_year(is_leap, first_date, first_day, max_year)
        max_year = year - 1
        allowed_years.append(year)
    return allowed_years


def get_lowest_frequency(all_frequencies):
    """ Find the shortest frequency from given ones. """
    return next((freq for freq in (TS, H, D, M, A, RP) if freq in all_frequencies))


def convert_raw_dates(raw_dates, year):
    """ Transform raw E+ date and time data into datetime.datetime objects. """
    dates = {}
    for frequency, value in raw_dates.items():
        dates[frequency] = generate_datetime_dates(value, year)
    return dates


def convert_raw_date_data(
    raw_dates,  #: Dict[str, List[EsoTimestamp]],
    days_of_week,  #: Dict[str, List[str]],
    year,  #: Optional[int],
):  # -> Dict[str, List[datetime]]:
    """ Convert EnergyPlus dates into standard datetime format. """
    lowest_frequency = get_lowest_frequency(list(raw_dates.keys()))
    if lowest_frequency in {TS, H, D}:
        lowest_frequency_values = raw_dates[lowest_frequency]
        is_leap = is_leap_year_ts_to_d(lowest_frequency_values)
        first_date = lowest_frequency_values[0]
        first_day = days_of_week[lowest_frequency][0]
        if year is None:
            year = seek_year(is_leap, first_date, first_day, 2020)
        else:
            validate_year(year, is_leap, first_date, first_day)
    else:
        # allow any year defined or set EnergyPlus default 2002
        year = year if year else 2002
    dates = convert_raw_dates(raw_dates, year)
    return update_start_dates(dates)
