import sqlite3
from datetime import timedelta, datetime

from db_esofile_reader import Variable
from db_esofile_reader.constants import *

DATA_TABLE = "ReportData"
DATA_DICT_TABLE = "ReportDataDictionary"
TIME_TABLE = "Time"


def to_eso_frequency(sql_frequency):
    """ Convert '.sql' frequency type to '.eso'. """
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
    """ Convert '.eso' frequency type to '.sql'. """
    if eso_frequency is None:
        frequency = None
    else:
        frequencies = {
            TS: "Zone Timestep",
            H: "Hourly",
            D: "Daily",
            M: "Monthly",
            RP: "Run Period",
            A: "Annual"
        }
        frequency = frequencies[eso_frequency]
    return frequency


def eso_to_sql_variable(variable):
    """ Convert 'Variable' to be compatible with sql queries. """
    sql_columns = ["ReportingFrequency", "KeyValue", "Name", "Units"]
    sql_variable = {}
    for v, c in zip(variable, sql_columns):
        if c == "ReportingFrequency":
            # SQL uses different key words to define frequency
            v = to_sql_frequency(v)
        if v is not None:
            sql_variable[c] = v
    return sql_variable


def data_dict_statement(columns, alike):
    """ Create statement to fetch matching data dict rows. """
    statement = "SELECT ReportDataDictionaryIndex, ReportingFrequency, KeyValue, Name, Units" \
                " FROM ReportDataDictionary"
    eq = " LIKE ?" if alike else "=?"
    conditions = [c + eq for c in columns]
    statement += " WHERE " + " AND ".join(conditions) if conditions else ""
    return statement


def add_wild_cards(search_tuple):
    """ Add wild card characters for 'LIKE' query. """
    return tuple(["%" + s + "%" for s in search_tuple])


def fetch_data_dict_rows(conn, variable, alike):
    """ Get all rows matching given 'Variable' request. """
    sql_variable = eso_to_sql_variable(variable)
    statement = data_dict_statement(sql_variable.keys(), alike)
    if sql_variable:
        place_holders = tuple(sql_variable.values())
        if alike:
            place_holders = add_wild_cards(place_holders)
        res = conn.execute(statement, place_holders)
    else:
        res = conn.execute(statement)
    return res


def to_string(unicode_variable):
    """ Convert 'variable unicode field names to string field names. """
    return Variable(*map(lambda x: str(x), unicode_variable))


def get_ids_dict(conn, variables, alike):
    """ Find id : Variable pairs for given 'Variable' request. """
    ids_dict = {}
    for variable in variables:
        rows = fetch_data_dict_rows(conn, variable, alike)
        for id_, frequency, key, type_, units in rows:
            unicode_variable = Variable(to_eso_frequency(frequency), key, type_, units)
            ids_dict[id_] = to_string(unicode_variable)
    return ids_dict


def create_placeholders(id_, start_date, end_date):
    """ Create an appropriate placeholder tuple. """
    placeholders = [id_]
    if start_date:
        placeholders.extend(
            [start_date.year, start_date.month, start_date.day, start_date.hour,
             start_date.minute]
        )
    if end_date:
        placeholders.extend(
            [end_date.year, end_date.month, end_date.day, end_date.hour, end_date.minute]
        )
    return tuple(placeholders)


def validate_time(timestamp, start_date, end_date):
    """ Check if given timestamp lies between start and end dates. """
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
    """ Fetch output values with associated timestamp. """
    statement = "SELECT ReportData.Value, " \
                "Time.IntervalType, Time.Year, Time.Month, Time.Day, Time.Hour, Time.Minute" \
                " FROM ReportData" \
                " JOIN Time ON ReportData.TimeIndex = Time.TimeIndex" \
                " WHERE ReportData.ReportDataDictionaryIndex = ?"
    return conn.execute(statement, (id_,))


def get_sliced_outputs(conn, id_, start_date, end_date):
    """ Get array of output values for given variable id sliced by given dates. """
    results = []
    for row in get_output_rows_with_time(conn, id_):
        timestamp = parse_sql_timestamp(row[1:])
        if validate_time(timestamp, start_date, end_date):
            results.append(row[0])
    return results


def get_outputs(conn, id_):
    """ Get array of output values for given variable id. """
    statement = "SELECT ReportData.Value FROM ReportData" \
                " WHERE ReportData.ReportDataDictionaryIndex = ?"
    return [r[0] for r in conn.execute(statement, (id_,))]


def dates_statement(frequency):
    """ Create statement to fetch numeric output rows. """
    switch = {TS: -1, H: 1, D: 2, M: 3, RP: 4, A: 5}
    statement = "SELECT Time.IntervalType, Time.Year, Time.Month, Time.Day," \
                " Time.Hour, Time.Minute FROM Time" \
                " WHERE Time.IntervalType = {}".format(switch[frequency.lower()])
    return statement


def parse_sql_timestamp(time_row):
    """ Convert EnerguPlus timestamp to standard datetime. """
    interval, year, month, day, hour, minute = time_row
    year = 2002 if (year == 0 or year is None) else year
    if interval > 1:
        # let day, month, annual and runperiod timestamp to be set at step beginning
        hour = 0
        minute = 0
        if interval in {3, 4, 5}:
            day = 1
    if hour == 24:
        # Convert last step of day
        shifted_datetime = datetime(year, month, day, hour - 1)
        corrected_datetime = shifted_datetime + timedelta(hours=1)
    else:
        corrected_datetime = datetime(year, month, day, hour, minute)
    return corrected_datetime


def parse_sql_timestamps(time_rows):
    """ Convert EnergyPlus timestamps to standard datetime. """
    timestamps = []
    for row in time_rows:
        timestamps.append(parse_sql_timestamp(row))
    return timestamps


def _get_timestamps(conn, frequency):
    statement = dates_statement(frequency)
    rows = conn.execute(statement)
    return parse_sql_timestamps(rows)


def get_timestamps_from_sql(path, frequency):
    """ Fetch timestamps for given frequency. """
    conn = sqlite3.connect(path)
    timestamps = _get_timestamps(conn, frequency)
    conn.close()
    return timestamps


def get_results_from_sql(path, variables, alike=False, start_date=None, end_date=None):
    """
    Extract output values from given EnergyPlus .sql file.

    Parameters
    ----------
    path : str
        A path to EnergyPlus .sql file output.
    variables : Variable or List of Variable
        Requested output variables.
    alike : default False, bool
        Specify if full string or only part of variable attribute
        needs to match, it's case insensitive in both cases.
    start_date : default None, datetime.datetime
        Lower datetime interval boundary, inclusive.
    end_date : default None, datetime.datetime
        Upper datetime interval boundary, inclusive.

    Returns
    -------
    dict of {Variable, list of float}

    """
    conn = sqlite3.connect(path)
    variables = [variables] if isinstance(variables, Variable) else variables
    ids_dict = get_ids_dict(conn, variables, alike)
    outputs = {}
    for id_, variable in ids_dict.items():
        if start_date or end_date:
            outputs[variable] = get_sliced_outputs(conn, id_, start_date, end_date)
        else:
            outputs[variable] = get_outputs(conn, id_)
    conn.close()
    return outputs
