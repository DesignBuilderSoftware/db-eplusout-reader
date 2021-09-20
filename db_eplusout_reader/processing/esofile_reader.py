import re
from collections import defaultdict, namedtuple
from datetime import datetime
from functools import partial

from db_eplusout_reader.constants import A, D, H, M, RP, TS
from db_eplusout_reader.exceptions import (
    BlankLineError,
    IncompleteFile,
    InvalidLineSyntax,
)
from db_eplusout_reader.processing.esofile_time import EsoTimestamp
from db_eplusout_reader.processing.raw_eso_data import RawOutputData

ENVIRONMENT_LINE = 1
TIMESTEP_OR_HOURLY_LINE = 2
DAILY_LINE = 3
MONTHLY_LINE = 4
RUNPERIOD_LINE = 5
ANNUAL_LINE = 6

Variable = namedtuple("Variable", "key type units")


def get_eso_file_version(raw_version):
    """Return eso file version as an integer (i.e.: 860, 890)."""
    version = raw_version.strip()
    start = version.index(" ")
    return int(version[(start + 1) : (start + 6)].replace(".", ""))


def get_eso_file_timestamp(timestamp):
    """Return date and time of the eso file generation as a Datetime."""
    timestamp = timestamp.split("=")[1].strip()
    return datetime.strptime(timestamp, "%Y.%m.%d %H:%M")


def process_statement_line(line):
    """Extract the version and time of the file generation."""
    # Program Version,EnergyPlus, Version 8.9.0-40101eaafd, YMD=2020.01.08 16:15
    _, raw_version, timestamp = line.rsplit(",", 2)
    version = get_eso_file_version(raw_version)
    timestamp = get_eso_file_timestamp(timestamp)
    return version, timestamp


def process_header_line(line):
    """
    Process E+ dictionary line and populate period header dictionaries.

    The goal is to process line syntax:
        ID, number of results, key name - zone / environment, variable name [units] !timestamp [info] # noqa E501

    Parameters
    ----------
    line : str
        A raw eso file line.

    Returns
    -------
    tuple of (int, str, str, str, str)
        Processed line tuple (ID, key name, variable name, units, frequency)

    """
    pattern = re.compile(r"^(\d+),(\d+),(.*?)(?:,(.*?) ?\[| ?\[)(.*?)\] !(\w*)")

    # this raises attribute error when there's some unexpected line syntax
    raw_line_id, _, key, type_, units, frequency = pattern.search(line).groups()
    line_id = int(raw_line_id)

    # 'type' variable is 'None' for 'Meter' variable
    if type_ is None:
        type_ = key
        key = "Cumulative Meter" if "Cumulative" in key else "Meter"

    return line_id, key, type_, units, frequency.lower()


def read_header(eso_file):
    """
    Read header dictionary of the eso file.

    The file is being read line by line until the 'End of TableType Dictionary'
    is reached. Raw line is processed and the line is added as an item to
    the header_dict dictionary.

    Parameters
    ----------
    eso_file : EsoFile
        Opened EnergyPlus result file.

    Returns
    -------
    dict of {str : dict of {Variable : int}}
        A dictionary of eso file header line with populated values.

    """
    header = defaultdict(partial(defaultdict))
    while True:
        raw_line = next(eso_file)
        try:
            line_id, key, type_, units, frequency = process_header_line(raw_line)
        except AttributeError as error:
            if "End of Data Dictionary" in raw_line:
                break
            if raw_line == "\n":
                raise BlankLineError("Empty line!") from error
            raise InvalidLineSyntax(
                "Unexpected line syntax: '{}'!".format(raw_line)
            ) from error
        header[frequency][Variable(key, type_, units)] = line_id
    return header


def process_ts_h_d_frequency_line(line_id, data):
    """
    Process sub-hourly, hourly and daily frequency line.

    Parameters
    ----------
    line_id : int
        An id of the frequency.
    data : list of str
        Line line passed as a list of strings (without ID).

    Note
    ----
    Data by given frequency:
        timestep, hourly : [Day of Simulation, Month, Day of Month,
                        DST Indicator, Hour, StartMinute, EndMinute, DayType]
        daily : [Cumulative Day of Simulation, Month, Day of Month,DST Indicator, DayType]

    Returns
    -------
        frequency identifier and numeric date time information and day of week..

    """

    def parse_timestep_or_hourly_frequency():
        """Process TS or H frequency entry and return frequency identifier."""
        # omit day of week in conversion
        items = [int(float(item)) for item in data[:-1]]
        frequency = EsoTimestamp(items[1], items[2], items[4], items[6])

        # check if frequency is timestep or hourly frequency
        if items[5] == 0 and items[6] == 60:
            return H, frequency, data[-1].strip()
        return TS, frequency, data[-1].strip()

    def parse_daily_frequency():
        """Populate D list and return identifier."""
        # omit day of week in in conversion
        i = [int(item) for item in data[:-1]]
        return D, EsoTimestamp(i[1], i[2], 0, 0), data[-1].strip()

    categories = {
        TIMESTEP_OR_HOURLY_LINE: parse_timestep_or_hourly_frequency,
        DAILY_LINE: parse_daily_frequency,
    }
    return categories[line_id]()


def process_month_rp_frequency_line(line_id, data):
    """
    Process monthly, annual or runperiod frequency line.

    Parameters
    ----------
    line_id : int
        An id of the frequency.
    data : list of str
        Line line passed as a list of strings (without ID).

    Note
    ----
    Data by given frequency:
        monthly : [Cumulative Day of Simulation, Month]
        annual : [Year] (only when custom weather file is used) otherwise [int]
        runperiod :  [Cumulative Day of Simulation]

    Returns
    -------
        frequency identifier and numeric date time information and day of week.

    """

    def parse_monthly_frequency():
        """Populate M list and return identifier."""
        return M, EsoTimestamp(int(data[1]), 1, 0, 0), int(data[0])

    def parse_runperiod_frequency():
        """Populate RP list and return identifier."""
        return RP, EsoTimestamp(1, 1, 0, 0), int(data[0])

    def parse_annual_frequency():
        """Populate A list and return identifier."""
        return A, EsoTimestamp(1, 1, 0, 0), None

    categories = {
        MONTHLY_LINE: parse_monthly_frequency,
        RUNPERIOD_LINE: parse_runperiod_frequency,
        ANNUAL_LINE: parse_annual_frequency,
    }
    return categories[line_id]()


def split_raw_line(raw_line):
    split_line = raw_line.split(",")
    line_id = int(split_line[0])
    line = split_line[1:]
    return line_id, line


def process_frequency_line(line_id, line, all_raw_outputs, header, raw_outputs):
    if line_id == ENVIRONMENT_LINE:
        # initialize variables for current environment
        environment_name = line[0].strip()
        raw_outputs = RawOutputData(environment_name, header)
        all_raw_outputs.append(raw_outputs)
        frequency = None
    else:
        if line_id > DAILY_LINE:
            frequency, date, n_days = process_month_rp_frequency_line(line_id, line)
            raw_outputs.cumulative_days[frequency].append(n_days)
        else:
            frequency, date, day = process_ts_h_d_frequency_line(line_id, line)
            raw_outputs.days_of_week[frequency].append(day)

        # Populate last environment list with frequency line
        raw_outputs.dates[frequency].append(date)

        # Populate current step for all result ids with nan values.
        # This is in place to avoid issues for variables which are not
        # reported during current frequency
        raw_outputs.initialize_next_outputs_step(frequency)
    return raw_outputs, frequency


def read_body(eso_file, highest_frequency_id, header):
    """
    Read body of the eso file.

    The line from eso file is processed line by line until the
    'End of Data' is reached.

    Index 1-5 for eso file generated prior to E+ 8.9 or 1-6 from E+ 8.9
    further, indicates that line is an frequency.

    Parameters
    ----------
    eso_file : file
        Opened EnergyPlus result file.
    highest_frequency_id : int
        A maximum index defining an frequency (higher is considered a result)
    header : dict of {str: dict of {Variable : list of int}}
        Processed header dictionary.

    Returns
    -------
    list of RawOutputData
        Processed ESO file data.

    """
    all_raw_outputs = []
    raw_outputs = None
    frequency = None
    while True:
        raw_line = next(eso_file)
        try:
            line_id, line = split_raw_line(raw_line)

            # distribute outputs into relevant bins
            if line_id <= highest_frequency_id:
                raw_outputs, frequency = process_frequency_line(
                    line_id, line, all_raw_outputs, header, raw_outputs
                )
            else:
                # current line represents a result, replace nan values from the last step
                res = float(line[0])
                raw_outputs.outputs[frequency][line_id][-1] = res

        except ValueError as error:
            if "End of Data" in raw_line:
                break
            if raw_line == "\n":
                raise BlankLineError("Empty line!") from error
            raise InvalidLineSyntax(
                "Unexpected line syntax: '{}'!".format(raw_line)
            ) from error

    return all_raw_outputs


def read_file(file):
    """Read raw EnergyPlus output file."""
    # process first few standard lines, ignore timestamp
    version, _ = process_statement_line(next(file))
    last_standard_item_id = 6 if version >= 890 else 5

    # Skip standard reporting frequencys
    for _ in range(last_standard_item_id):
        next(file)

    # Read header to obtain a header dictionary of EnergyPlus
    # outputs and initialize dictionary for output values
    header = read_header(file)

    # Read body to obtain outputs and environment dictionaries
    return read_body(file, last_standard_item_id, header)


def process_eso_file(file_path):
    """Trigger eso file processing."""
    try:
        with open(file_path, "r") as file:
            return read_file(file)
    except StopIteration as error:
        raise IncompleteFile("File '{}' is not complete!".format(file_path)) from error
