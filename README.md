# db-esofile-reader
## A package to read results from EnergyPlus output files.

'Variable' is a named tuple to define expected output variables.

    v = Variable(
        frequency="hourly",
        key="PEOPLE BLOCK1:ZONE2",
        type="Zone Thermal Comfort Fanger Model PMV",
        units=""
    )

'get_results' is the main method to get results from given file.

    results = get_results(r"C:\some\path\eplusout.sql", variables=v)
    
returned values is a ResultsDictionary dict like class with some
handy properties to easily get numeric and variable data.

    results.sorted_items
    results.scalar
    results.first_array
    results.first_variable
    results.variables
    results.arrays


When one (or multiple) 'Variable' fields would be set as None,
filtering for specific part of variable will not be applied.

Variable(None, None, None, None) returns all outputs.
Variable("hourly", None, None, None) returns all 'hourly' outputs.

Frequency constants {TS, H, D, M, A, RP} can be imported
from db_esofile_reader.constants.

Examples
--------
```Python
from db_esofile_reader import Variable, get_results
from db_esofile_reader.constants import *
from datetime import datetime

variables = [
     Variable(RP, "", "Electricity:Facility", "J"), # standard meter
     Variable(RP, "Cumulative", "Electricity:Facility", "J"), # cumulative meter
     Variable(RP, None, None, None), # get all runperiod outputs
     Variable(H, "PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
     Variable(H, "PEOPLE BLOCK", "Zone Thermal Comfort Fanger Model PMV", "")
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

# runperiod timestamp always defaults to datetime(2002, 1, 1) so following
# statement returns empty arrays for runperiod variables

alike_results = get_results(
    r"C:\some\path\eplusout.sql",
    variables=variables,
    alike=True,
    start_date=datetime(2002, 5, 1, 0),
    end_date=datetime(2002, 5, 31, 23, 59)
)
```
