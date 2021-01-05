# db-eplusout-reader ![Tests](https://github.com/DesignBuilderSoftware/db-esofile-reader/workflows/Tests/badge.svg)
## A package to read results from EnergyPlus output files.

'Variable' is a named tuple to define expected output variables.

    v = Variable(
        frequency="hourly",
        key="PEOPLE BLOCK1:ZONE2",
        type="Zone Thermal Comfort Fanger Model PMV",
        units=""
    )
   
When one (or multiple) 'Variable' fields would be set as None,
filtering for specific part of variable will not be applied.

Variable(None, None, None, None) returns all outputs.
Variable("hourly", None, None, None) returns all 'hourly' outputs.


'get_results' works as the main method to get results from given file.

    results = get_results(r"C:\some\path\eplusout.sql", variables=v)
    
It returns a ResultsDictionary dict like class with some
handy properties to easily get numeric and variable data.

    results.scalar
    results.first_array
    results.first_variable
    results.variables
    results.arrays

ResultsDictionary is a subclass of OrderedDict - variables are returned in a 
requested order. If a single requested variable returns multiple variables 
(either using 'None' fields or 'alike') this 'sequence' is ordered alphabetically.

Frequency constants {TS, H, D, M, A, RP} can be imported
from db_esofile_reader.constants.

Examples
--------

```Python
from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import *
from datetime import datetime

variables = [
    Variable(RP, "", "Electricity:Facility", "J"),  # standard meter
    Variable(RP, "Cumulative", "Electricity:Facility", "J"),  # cumulative meter
    Variable(D, None, None, None),  # get all daily outputs
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
