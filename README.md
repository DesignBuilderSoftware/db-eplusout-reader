# db-eplusout-reader ![Tests](https://github.com/DesignBuilderSoftware/db-eplusout-reader/workflows/Tests/badge.svg)
## A tool to fetch results from EnergyPlus output files.

Extract requested results using 'get_results' function. Expected arguments are file path, 
list of variables and output interval (frequency).

'Variable' is a named tuple to define single or multiple requested outputs.

```python
v = Variable(
    key="PEOPLE BLOCK1:ZONE2",
    type="Zone Thermal Comfort Fanger Model PPD",
    units="%"
)
```

When one (or multiple) 'Variable' fields would be set as None, filtering for specific part 
of variable will not be applied.

```python
Variable(None, None, None)  # returns all outputs
Variable(None, None, "J")   # returns all 'energy' outputs.
```

Frequency defines output interval - it can be one of "timestep", "hourly", "daily",
"monthly" "annual" and "runperiod". Constants module includes shorthand TS, H, D, M, A, RP constants.
Function needs to be called multiple times to get results from various intervals.

Alike optional argument defines whether variable search should filter results by
full or just a substring (search is always case-insensitive).

Start and end date optional arguments can slice resulting array based on timestamp data.


Examples
--------
```python
from datetime import datetime

from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import D


variables = [
     Variable("", "Electricity:Facility", "J"), # standard meter
     Variable("Cumulative", "Electricity:Facility", "J"), # cumulative meter
     Variable(None, None, None), # get all outputs
     Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
     Variable("PEOPLE BLOCK", "Zone Thermal Comfort Fanger Model PMV", "")
]

# get results for variables fully matching output variables
# the last variable above won't be found as variable 'key' does not fully match
# variables will be extracted from 'daily' interval results
# start and end date slicing is not applied

explicit_results = get_results(
    r"C:\some\path\eplusout.sql",
    variables=variables,
    frequency=D,
    alike=False
)

# 'alike' argument is set to True so even substring match is enough to match variable
# the last variable will be found ("PEOPLE BLOCK" matches "PEOPLE BLOCK1:ZONE2")
# start and end dates are specified so only 'May' data will be included

alike_results = get_results(
    r"C:\some\path\eplusout.sql",
    variables=variables,
    frequency=D,
    alike=True,
    start_date=datetime(2002, 5, 1, 0),
    end_date=datetime(2002, 5, 31, 23, 59)
)
```

Returned value is 'ResultsDictionary' - dictionary-like class with 'Variable' tuples as keys and 
list of floats as values.

ResultsDictionary holds multiple properties to easily access specific outputs.

```python
from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import M

variables = [
    Variable("", "Electricity:Facility", "J"),
    Variable("PEOPLE BLOCK1:ZONE1", "Zone Thermal Comfort Fanger Model PMV", ""),
    Variable("PEOPLE BLOCK1:ZONE2", "Zone Thermal Comfort Fanger Model PMV", ""),
]

results = get_results(p, variables=variables, frequency=M, alike=False)

results.frequency
# 'monthly'

results.time_series
# [
#    datetime.datetime(2013, 1, 1, 0, 0),
#    datetime.datetime(2013, 2, 1, 0, 0),
#    datetime.datetime(2013, 3, 1, 0, 0),
#    ...
# ]
results.scalar
# 6061634975.339457

results.first_variable
# Variable(key='', type='Electricity:Facility', units='J')

results.first_array
# [
#    6061634975.339457,
#    5281325837.465538,
#    5561245113.000078,
#    ...
# ]

results.variables
# [
#   Variable(key='', type='Electricity:Facility', units='J'),
#   Variable(key='PEOPLE BLOCK1:ZONE1', type='Zone Thermal Comfort Fanger Model PMV', units=''),
#   Variable(key='PEOPLE BLOCK1:ZONE2', type='Zone Thermal Comfort Fanger Model PMV', units=''),
# ]

results.arrays
# [
#     [
#         6061634975.339457,
#         5281325837.465538,
#         5561245113.000078,
#         ...
#     ],
#     [
#         -1.4380301899651864,
#         -1.4643449253153416,
#         -1.0314397512150693,
#         ...
#     ],
#     [
#         -1.3833280647182002,
#         -1.4166039181936205,
#         ...
#     ],
# ]
```
