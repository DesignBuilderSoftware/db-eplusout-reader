# db-esofile-reader
A package to read results from EnergyPlus output files.

'get_results' is the main method to get results from given file.

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
     Variable("runperiod", None, None, None), # get all runperiod outputs
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
