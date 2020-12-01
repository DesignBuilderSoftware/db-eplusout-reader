import os

from db_esofile_reader.db_esofile import DBEsoFile, DBEsoFileCollection
from db_esofile_reader.sql_reader import get_results_from_sql


def get_results(file_or_path, variables, alike=False, start_date=None, end_date=None):
    """
    Extract results from given file.

    'Variable' is a named tuple to define expected output variables.

    v = Variable(
        frequency="hourly",
        key="PEOPLE BLOCK1:ZONE2",
        type="Zone Thermal Comfort Fanger Model",
        units=None
    )

    When one (or multiple) 'Variable' fields would be set as None,
    filtering for specific part of variable will not be applied.

    Variable(None, None, None, None) returns all outputs
    Variable("hourly", None, None, None) returns all 'hourly' outputs.

    Note that frequency constants {TS, H, D, M, A, RP} can be imported
    from db_esofile_reader.constants.

    Examples
    --------
    from db_esofile_reader import Variable, get_results
    from datetime import datetime

    variables = [
         Variable("runperiod", "", "Electricity:Facility", "J"), # standard meter
         Variable("runperiod", "Cumulative", "Electricity:Facility", "J"), # cumulative meter
         Variable("daily", None, None, None), # get all daily outputs
         Variable("hourly", "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
         Variable("hourly", "PEOPLE BLOCK", "Zone Thermal Comfort Fanger Model PMV", "")
    ]

    # get results for variables fully matching data dictionary values
    # the last variable won't be found, start and end date slicing is not applied

    results = get_results(
        r"C:\some\path\eplusout.sql",
        variables=variables,
        alike=False
    )

    # get results for variables matching only substrings of data dictionary values
    # the last variable will be found, only 'May' data will be included

    results = get_results(
        r"C:\some\path\eplusout.sql",
        variables=variables,
        alike=False,
        start_date=datetime(2002, 5, 1, 0),
        end_date=datetime(2002, 5, 31, 23, 59)
    )

    Parameters
    ----------
    file_or_path : DBEsoFile, DBEsoFileCollection or PathLike
        A processed EnergyPlus .eso file, path to unprocessed .eso file
        or path to unprocessed .sql file.
    variables : Variable or List of Variable
        Requested output variables.
    alike : default False, bool
        Specify if full string or only part of variable attribute
        needs to match, filtering is case insensitive in both cases.
    start_date : default None, datetime.datetime
        Lower datetime interval boundary, inclusive.
    end_date : default None, datetime.datetime
        Upper datetime interval boundary, inclusive.

    Returns
    -------
    ResultsDictionary : Dict of {Variable, list of float}
        A dictionary like class with some properties to easily extract output values.

    """
    if isinstance(file_or_path, str):
        _, ext = os.path.splitext(file_or_path)
        if ext == ".sql":
            results = get_results_from_sql(
                file_or_path, variables, alike=alike, start_date=start_date, end_date=end_date
            )
        elif ext == ".eso":
            raise NotImplemented("Sorry, this has not been implemented yet.")
        else:
            raise TypeError("Unsupported file type '{}' provided!".format(ext))
    else:
        if isinstance(file, (DBEsoFile, DBEsoFileCollection)):
            raise NotImplemented("Sorry, this has not been implemented yet.")
        else:
            raise TypeError("Unsupported class '{}' provided!".format(type(file).__name__))
    return results
