"""Optional Parquet I/O for results dictionaries.

Parquet is handy for object-storage workflows. Support is an optional
extension: install the extra to enable it::

    pip install db-eplusout-reader[parquet]

A results dictionary is stored as a columnar table with one column per
variable plus an optional ``timestamp`` column. The variable fields
(key, type, units) and the reporting frequency are preserved in Arrow
metadata so the table round-trips back into a ``ResultsDictionary``.
"""

from db_eplusout_reader.processing.esofile_reader import Variable
from db_eplusout_reader.results_dict import ResultsDictionary

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - exercised only without the extra
    pa = None
    pq = None

_TIMESTAMP_COLUMN = "timestamp"
_ROLE_KEY = b"db_role"
_ROLE_TIMESTAMP = b"timestamp"
_ROLE_VARIABLE = b"variable"
_FREQUENCY_KEY = b"frequency"
_KEY_KEY = b"key"
_TYPE_KEY = b"type"
_UNITS_KEY = b"units"


def _require_pyarrow():
    if pa is None:
        raise ImportError(
            "Parquet support requires the optional 'parquet' extra. "
            "Install it with: pip install db-eplusout-reader[parquet]"
        )


def _encode(value):
    """Encode a (possibly None) variable field as bytes for Arrow metadata."""
    return (value if value is not None else "").encode("utf-8")


def to_parquet(results_dictionary, path, **kwargs):
    """
    Save a results dictionary as a Parquet file.

    Parameters
    ----------
    results_dictionary : ResultsDictionary
        Results to store. Must contain at least one variable.
    path : os.PathLike
        Destination Parquet file path.
    **kwargs
        Additional keyword arguments forwarded to ``pyarrow.parquet.write_table``
        (e.g. ``compression``).

    Returns
    -------
    None

    """
    _require_pyarrow()
    fields = []
    columns = []

    if results_dictionary.time_series:
        fields.append(
            pa.field(
                _TIMESTAMP_COLUMN,
                pa.timestamp("us"),
                metadata={_ROLE_KEY: _ROLE_TIMESTAMP},
            )
        )
        columns.append(pa.array(results_dictionary.time_series, type=pa.timestamp("us")))

    for variable, array in zip(results_dictionary.variables, results_dictionary.arrays):
        metadata = {
            _ROLE_KEY: _ROLE_VARIABLE,
            _KEY_KEY: _encode(variable.key),
            _TYPE_KEY: _encode(variable.type),
            _UNITS_KEY: _encode(variable.units),
        }
        name = "{}|{}|{}".format(variable.key, variable.type, variable.units)
        fields.append(pa.field(name, pa.float64(), metadata=metadata))
        columns.append(pa.array(array, type=pa.float64()))

    schema = pa.schema(fields, metadata={_FREQUENCY_KEY: _encode(results_dictionary.frequency)})
    pq.write_table(pa.table(columns, schema=schema), path, **kwargs)


def read_parquet(path):
    """
    Read a results dictionary from a Parquet file written by ``to_parquet``.

    Parameters
    ----------
    path : os.PathLike
        Parquet file path.

    Returns
    -------
    ResultsDictionary
        Reconstructed results, including frequency and time series.

    """
    _require_pyarrow()
    table = pq.read_table(path)
    schema = table.schema

    frequency = ""
    if schema.metadata and _FREQUENCY_KEY in schema.metadata:
        frequency = schema.metadata[_FREQUENCY_KEY].decode("utf-8")

    results_dictionary = ResultsDictionary(frequency)
    time_series = None
    for i, field in enumerate(schema):
        metadata = field.metadata or {}
        role = metadata.get(_ROLE_KEY)
        column = table.column(i).to_pylist()
        is_timestamp = role == _ROLE_TIMESTAMP or (
            role is None and field.name == _TIMESTAMP_COLUMN
        )
        if is_timestamp:
            time_series = column
        else:
            variable = Variable(
                metadata.get(_KEY_KEY, b"").decode("utf-8"),
                metadata.get(_TYPE_KEY, b"").decode("utf-8"),
                metadata.get(_UNITS_KEY, b"").decode("utf-8"),
            )
            results_dictionary[variable] = column

    results_dictionary.time_series = time_series
    return results_dictionary
