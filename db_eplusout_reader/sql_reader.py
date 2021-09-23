import sqlite3
from collections import OrderedDict
from datetime import datetime, timedelta

from db_eplusout_reader.constants import RP, TS, A, D, H, M
from db_eplusout_reader.processing.esofile_reader import Variable
from db_eplusout_reader.results_dict import ResultsDictionary

DATA_TABLE = "ReportData"
DATA_DICT_TABLE = "ReportDataDictionary"
TIME_TABLE = "Time"


def to_eso_frequency(sql_frequency):
    """Convert '.sql' frequency type to '.eso'."""
    frequencies = {
        "Zone Timestep": TS,
        "Hourly": H,
        "Daily": D,
        "Monthly": M,
        "Run Period": RP,
        "Annual": A,
        "HVAC System Timestep": TS,
    }
    return frequencies[sql_frequency]


def to_sql_frequency(eso_frequency):
    """Convert '.eso' frequency type to '.sql'."""
    if eso_frequency is None:
        frequency = None
    else:
        frequencies = {
            TS: "Zone Timestep",
            H: "Hourly",
            D: "Daily",
            M: "Monthly",
            RP: "Run Period",
            A: "Annual",
        }
        frequency = frequencies[eso_frequency]
    return frequency


def eso_to_sql_variable(variable):
    """Convert 'Variable' to be compatible with sql queries."""
    sql_columns = ["KeyValue", "Name", "Units"]
    sql_variable = {}
    for variable, column in zip(variable, sql_columns):
        if variable is not None:
            sql_variable[column] = variable
    return sql_variable


def data_dict_statement(columns, alike):
    """Create statement to fetch matching data dict rows."""
    statement = (
        "SELECT ReportDataDictionaryIndex, ReportingFrequency, KeyValue, Name, Units"
        " FROM ReportDataDictionary WHERE ReportingFrequency =?"
    )
    eq_operater = " LIKE ?" if alike else "=?"
    conditions = [column + eq_operater for column in columns]
    if conditions:
        statement += "AND " + "AND ".join(conditions)
    return statement


def add_wild_cards(search_tuple):
    """Add wild card characters for 'LIKE' query."""
    return tuple("%" + s + "%" for s in search_tuple)


def fetch_data_dict_rows(conn, variable, sql_frequency, alike):
    """Get all rows matching given 'Variable' request."""
    sql_variable = eso_to_sql_variable(variable)
    statement = data_dict_statement(sql_variable.keys(), alike)
    if sql_variable:
        if alike:
            place_holders = add_wild_cards(sql_variable.values())
        else:
            place_holders = tuple(sql_variable.values())
        res = conn.execute(statement, (sql_frequency, *place_holders))
    else:
        res = conn.execute(statement, (sql_frequency,))
    return res


def to_string(unicode_variable):
    """Convert 'variable unicode field names to string field names."""
    return Variable(*map(lambda x: str(x), unicode_variable))


def get_unsorted_sub_dict(rows):
    unsorted_dict = {}
    for id_, frequency, key, type_, units in rows:
        unicode_variable = Variable(key, type_, units)
        variable = to_string(unicode_variable)
        unsorted_dict[id_] = variable
    return unsorted_dict


def sort_by_value(unsorted_dict):
    sorted_dct = OrderedDict()
    sorted_items = [item for item in sorted(unsorted_dict.items(), key=lambda x: x[1])]
    for key, value in sorted_items:
        sorted_dct[key] = value
    return sorted_dct


def get_ids_dict(conn, variables, sql_frequency, alike):
    """Find id : Variable pairs for given 'Variable' request."""
    all_ids_dict = OrderedDict()
    for variable in variables:
        rows = fetch_data_dict_rows(conn, variable, sql_frequency, alike)
        ids_dict = get_unsorted_sub_dict(rows)
        all_ids_dict.update(sort_by_value(ids_dict))
    return all_ids_dict


def validate_time(timestamp, start_date, end_date):
    """Check if given timestamp lies between start and end dates."""
    if start_date and end_date:
        valid = start_date <= timestamp <= end_date
    elif start_date:
        valid = timestamp >= start_date
    elif end_date:
        valid = timestamp <= end_date
    else:
        valid = True
    return valid


def get_output_rows_with_time(conn, id_):
    """Fetch output values with associated timestamp."""
    statement = (
        "SELECT ReportData.Value, "
        "Time.IntervalType, Time.Year, Time.Month, Time.Day, Time.Hour, Time.Minute"
        " FROM ReportData"
        " JOIN Time ON ReportData.TimeIndex = Time.TimeIndex"
        " WHERE ReportData.ReportDataDictionaryIndex = ?"
    )
    return conn.execute(statement, (id_,))


def get_sliced_outputs(conn, id_, start_date, end_date):
    """Get array of output values for given variable id sliced by given dates."""
    results = []
    for row in get_output_rows_with_time(conn, id_):
        timestamp = parse_sql_timestamp(row[1:])
        if validate_time(timestamp, start_date, end_date):
            results.append(row[0])
    return results


def get_outputs(conn, id_):
    """Get array of output values for given variable id."""
    statement = (
        "SELECT ReportData.Value FROM ReportData"
        " WHERE ReportData.ReportDataDictionaryIndex = ?"
    )
    return [r[0] for r in conn.execute(statement, (id_,))]


def dates_statement(frequency):
    """Create statement to fetch numeric output rows."""
    switch = {TS: -1, H: 1, D: 2, M: 3, RP: 4, A: 5}
    statement = (
        "SELECT Time.IntervalType, Time.Year, Time.Month, Time.Day,"
        " Time.Hour, Time.Minute FROM Time"
        " WHERE Time.IntervalType = {}".format(switch[frequency.lower()])
    )
    return statement


def parse_sql_timestamp(time_row):
    """Convert EnerguPlus timestamp to standard datetime."""
    interval, year, month, day, hour, minute = time_row
    year = 2002 if (year == 0 or year is None) else year

    # some fields may be none, 0 or 24 which is not compatible with datetime format
    if interval == 2:
        hour, minute = 0, 0
    elif interval == 3:
        day, hour, minute = 1, 0, 0
    elif interval in {4, 5}:
        month, day, hour, minute = 1, 1, 0, 0

    if hour == 24:
        # Convert last step of day
        shifted_datetime = datetime(year, month, day, hour - 1)
        corrected_datetime = shifted_datetime + timedelta(hours=1)
    else:
        corrected_datetime = datetime(year, month, day, hour, minute)
    return corrected_datetime


def parse_sql_timestamps(time_rows):
    """Convert EnergyPlus timestamps to standard datetime."""
    timestamps = []
    for row in time_rows:
        timestamps.append(parse_sql_timestamp(row))
    return timestamps


def filter_timestamps(timestamps, start_date, end_date):
    valid_timestamps = []
    for timestamp in timestamps:
        if validate_time(timestamp, start_date, end_date):
            valid_timestamps.append(timestamp)
    return valid_timestamps


def get_timestamps_from_sql(path, frequency, start_date=None, end_date=None):
    """Fetch timestamps for given frequency."""
    conn = sqlite3.connect(path)

    statement = dates_statement(frequency)
    rows = conn.execute(statement)
    timestamps = parse_sql_timestamps(rows)

    if start_date or end_date:
        timestamps = filter_timestamps(timestamps, start_date, end_date)

    conn.close()
    return timestamps


def get_results_from_sql(
    path, variables, frequency, alike=False, start_date=None, end_date=None
):
    """
    Extract output values from given EnergyPlus .sql file.

    Parameters
    ----------
    path : str
        A path to EnergyPlus .sql file output.
    variables : Variable or List of Variable
        Requested output variables.
    frequency : str
        An output interval, this can be one of {TS, H, D, M, A, RP} constants.
    alike : default False, bool
        Specify if full string or only part of variable attribute
        needs to match, it's case insensitive in both cases.
    start_date : default None, datetime.datetime
        Lower datetime interval boundary, inclusive.
    end_date : default None, datetime.datetime
        Upper datetime interval boundary, inclusive.

    Returns
    -------
    ResultsDictionary : Dict of {Variable, list of float}

    """
    conn = sqlite3.connect(path)
    variables = [variables] if isinstance(variables, Variable) else variables
    sql_frequency = to_sql_frequency(frequency)
    ids_dict = get_ids_dict(conn, variables, sql_frequency, alike)
    rd = ResultsDictionary(frequency)
    for id_, variable in ids_dict.items():
        if start_date or end_date:
            rd[variable] = get_sliced_outputs(conn, id_, start_date, end_date)
        else:
            rd[variable] = get_outputs(conn, id_)
    rd.time_series = get_timestamps_from_sql(path, frequency, start_date, end_date)
    conn.close()
    return rd
