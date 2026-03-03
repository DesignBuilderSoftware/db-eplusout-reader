# db-eplusout-reader

![Tests](https://github.com/DesignBuilderSoftware/db-eplusout-reader/workflows/Tests/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)

A tool to fetch results from EnergyPlus output files (`.sql` and `.eso` formats).

## Features

- Read results from both `.sql` (SQLite) and `.eso` (text) EnergyPlus output files
- Filter variables by key, type, and units
- Support for exact and substring (alike) matching
- Filter results by date range
- Export results to CSV
- Zero runtime dependencies

## DesignBuilder Compatibility

| DesignBuilder Version | Package Version |
|-----------------------|-----------------|
| < v7.2.0.028          | 0.2.0           |
| >= v7.2.0.028         | 0.3.x           |
| future release        | 0.4.0           |

## Installation

### Standalone Python Environment

```bash
pip install git+https://github.com/DesignBuilderSoftware/db-eplusout-reader.git
```

To install a specific version:

```bash
pip install git+https://github.com/DesignBuilderSoftware/db-eplusout-reader.git@v0.3.2
```

### DesignBuilder Integration

Since DesignBuilder does not always include the latest package release, you can manually update it:

**Option 1: Wheel Installation**

1. Download the `.whl` file from the [release page](https://github.com/DesignBuilderSoftware/db-eplusout-reader/releases)
2. Delete existing `db_eplusout_reader` folder in DesignBuilder's Python directory
3. Install with pip (may require admin mode):

```bash
python -m pip install "C:\path\to\db_eplusout_reader-x.x.x-py3-none-any.whl" --target "C:\Program Files\DesignBuilder\Python\Lib"
```

**Option 2: Manual Copy**

1. Download the source code `.zip` from the release page
2. Copy the `db_eplusout_reader` folder to DesignBuilder's Python `Lib` directory

## Usage

### Basic Concepts

**Variable**: A named tuple `(key, type, units)` that defines which outputs to extract.

```python
from db_eplusout_reader import Variable

# Specific variable
v = Variable(
    key="PEOPLE BLOCK1:ZONE2",
    type="Zone Thermal Comfort Fanger Model PPD",
    units="%"
)

# Use None to match any value for that field
Variable(None, None, None)  # returns all outputs
Variable(None, None, "J")   # returns all outputs with units "J"
Variable(None, "Temperature", None)  # returns all temperature outputs
```

**Frequency**: Output interval - one of `TS` (timestep), `H` (hourly), `D` (daily), `M` (monthly), `A` (annual), or `RP` (runperiod).

```python
from db_eplusout_reader.constants import TS, H, D, M, A, RP
```

### Reading SQL Files

For `.sql` files, use `get_results()` directly - SQLite handles caching efficiently:

```python
from db_eplusout_reader import Variable, get_results
from db_eplusout_reader.constants import H

results = get_results(
    r"C:\path\to\eplusout.sql",
    variables=[Variable(None, None, "C")],
    frequency=H
)
```

### Reading ESO Files

For `.eso` files, parse once and query multiple times to avoid re-reading:

```python
from db_eplusout_reader import DBEsoFile, Variable
from db_eplusout_reader.constants import H, D

# Parse the file once
eso = DBEsoFile.from_path(r"C:\path\to\eplusout.eso")

# Query multiple times without re-reading
results_temp = eso.get_results([Variable(None, None, "C")], H)
results_pressure = eso.get_results([Variable(None, None, "Pa")], H)
results_daily = eso.get_results([Variable(None, None, None)], D)
```

You can also pass the `DBEsoFile` object to `get_results()`:

```python
results = get_results(eso, variables=[Variable(None, None, "C")], frequency=H)
```

### Filtering Options

**Exact vs Substring Matching**

```python
# Exact match (default) - key must match exactly
results = get_results(path, variables, frequency=D, alike=False)

# Substring match - partial matches allowed
results = get_results(path, variables, frequency=D, alike=True)
# Variable("BLOCK", None, None) will match "PEOPLE BLOCK1:ZONE2"
```

**Date Range Filtering**

```python
from datetime import datetime

results = get_results(
    path,
    variables=variables,
    frequency=D,
    start_date=datetime(2002, 5, 1, 0),
    end_date=datetime(2002, 5, 31, 23, 59)
)
```

### Working with Results

`get_results()` returns a `ResultsDictionary` with useful properties:

```python
results = get_results(path, variables, frequency=M)

# Metadata
results.frequency      # 'monthly'
results.time_series    # [datetime(2013, 1, 1), datetime(2013, 2, 1), ...]

# Access data
results.variables      # List of matched Variable tuples
results.arrays         # List of value arrays (one per variable)
results.first_variable # First matched Variable
results.first_array    # Values for first variable
results.scalar         # First value of first array

# Iterate
for variable, values in results.items():
    print(f"{variable}: {len(values)} values")
```

### Export to CSV

```python
# Basic export
results.to_csv(r"C:\output.csv")

# With options
results.to_csv(
    r"C:\output.csv",
    explode_header=True,  # Split Variable into separate columns
    delimiter=",",        # CSV delimiter
    title="My Results",   # Add title row
    append=True           # Append to existing file
)
```

## Complete Example

```python
from datetime import datetime
from db_eplusout_reader import DBEsoFile, Variable, get_results
from db_eplusout_reader.constants import H, D, M

# Define variables to extract
variables = [
    Variable(None, "Electricity:Facility", "J"),
    Variable("PEOPLE BLOCK1:ZONE1", "Zone Thermal Comfort Fanger Model PMV", ""),
]

# === SQL File ===
sql_results = get_results(
    r"C:\path\to\eplusout.sql",
    variables=variables,
    frequency=M,
    alike=False
)

# === ESO File (parse once, query many) ===
eso = DBEsoFile.from_path(r"C:\path\to\eplusout.eso")

eso_results_monthly = eso.get_results(variables, M)
eso_results_hourly = eso.get_results(variables, H)
eso_results_filtered = eso.get_results(
    variables,
    H,
    start_date=datetime(2019, 1, 1),
    end_date=datetime(2019, 1, 31)
)

# === Work with results ===
print(f"Found {len(sql_results)} variables")
print(f"Time steps: {len(sql_results.time_series)}")
print(f"First variable: {sql_results.first_variable}")
print(f"First 5 values: {sql_results.first_array[:5]}")

# Export
sql_results.to_csv(r"C:\output.csv", explode_header=True)
```

## Development

### Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and [ruff](https://github.com/astral-sh/ruff) for linting/formatting.

```bash
# Install dependencies
uv sync --group dev

# Run tests
uv run pytest tests -v

# Run linting
uv run ruff check .
uv run ruff format .

# Run pre-commit hooks
uv run pre-commit run --all-files
```

### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
uv run pre-commit install
```

## License

MIT License - see [LICENSE](LICENSE) for details.
