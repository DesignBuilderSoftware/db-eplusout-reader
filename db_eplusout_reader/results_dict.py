import csv
import sys
from collections import OrderedDict

from db_eplusout_reader.exceptions import InvalidShape, NoResults
from db_eplusout_reader.processing.esofile_reader import Variable


class ResultsDictionary(OrderedDict):
    """
    A dictionary like class with enhanced functionality to easily extract output arrays.

    Properties
    ----------
    frequency : str
        EnergyPlus reporting interval.
    time_series : Optional, list of datetime
        Result timestamps.
    scalar : float
        First value of first variable.
    first_array : list of float
        Numeric array of first variable.
    first_variable : Variable
        First variable named tuple.
    variables : list of Variable
        All Variable named tuples.
    arrays : list of list of float
        All numeric arrays.

    Raises
    ------
    NoResults
        Is raised wne there are no relevant results to be fetched.

    """

    def __init__(self, frequency=""):
        super(ResultsDictionary, self).__init__()  # noqa: R1725
        self.frequency = frequency
        self.time_series = None

    @property
    def _items(self):
        if self:
            return list(self.items())
        raise NoResults("Cannot get items, Results dictionary is empty. ")

    @property
    def scalar(self):
        try:
            return self._items[0][1][0]
        except IndexError:
            raise NoResults("Cannot get scalar value, first array is empty!")

    @property
    def first_array(self):
        return self._items[0][1]

    @property
    def first_variable(self):
        return self._items[0][0]

    @property
    def variables(self):
        return [v[0] for v in self._items]

    @property
    def arrays(self):
        return [v[1] for v in self._items]

    def to_table(self, explode_header=True):
        """
        Get results in a table like format.

        Parameters
        ----------
        explode_header : bool
            Split variable into multiple rows if true,
            otherwise put one variable into one row.

        Returns
        -------
        list of list of {float, str or datetime}
            Table like nested list of lists.

        """
        return ResultsHandler.convert_dict_to_table(self, explode_header)

    def to_csv(
        self, path, explode_header=True, delimiter=",", append=False, title="", **kwargs
    ):
        """
        Save results as a csv file.

        Parameters
        ----------
        path : os.PathLike
            Defines a file path of the csv file.
        explode_header : bool
            Split variable into multiple rows if true,
            otherwise put one variable into one cell.
        delimiter : str, default ","
            Csv delimiter character.
        append : bool, default False
            Add results below the last row instead of replacing the .csv.
        title : str
            Add row with given text.
        **kwargs
            Key word arguments passed to csv writer.

        Returns
        -------
            None

        """
        table = ResultsHandler.convert_dict_to_table(self, explode_header)
        ResultsWriter.write_table_to_csv(
            table, path, delimiter, append, title, **kwargs
        )


class ResultsHandler:
    """Handles results dictionary transformations."""

    @classmethod
    def _explode_header(cls, header):
        """Split header into multiple rows."""
        header_rows = []
        for field in Variable._fields:
            row = []
            for variable in header:
                row.append(getattr(variable, field))
            header_rows.append(row)
        return header_rows

    @classmethod
    def _insert_index_column(cls, table, index, offset):
        """Add first column with header names and datetime / range data."""
        index_column = ["" for _ in range(offset)] + index
        for i, item in enumerate(index_column):
            table[i].insert(0, item)

    @classmethod
    def convert_dict_to_table(cls, results_dictionary, explode_header):
        """
        Convert dictionary like into array of arrays

        Parameters
        ----------
        results_dictionary : ResultsDictionary
            Results dictionary input.
        explode_header : bool
            Split variable into multiple rows if true,
            otherwise put one variable into one row.

        Returns
        -------
        list of list of {float, str or datetime}
            Table like nested list of lists.

        """
        header = results_dictionary.variables
        n_rows = len(results_dictionary[header[0]])
        table = cls._explode_header(header) if explode_header else [header]
        for i in range(0, n_rows):
            row = []
            for array in results_dictionary.arrays:
                row.append(array[i])
            table.append(row)
        if results_dictionary.time_series:
            offset = len(Variable._fields) if explode_header else 1
            cls._insert_index_column(table, results_dictionary.time_series, offset)
        return table

    @classmethod
    def get_table_shape(cls, table):
        """Read table dimensions."""
        n_rows = len(table)
        iterator = iter(table)
        n_columns = len(next(iterator))
        if not all(len(column) == n_columns for column in iterator):
            raise InvalidShape("Something is wrong, table is not uniform.")
        return n_rows, n_columns


class ResultsWriter:
    """Handle results dictionary i/o operations."""

    @classmethod
    def write_table_to_csv(cls, table, path, delimiter, append, title, **kwargs):
        """Write given table as a .csv file."""
        if sys.version_info[0] == 3:
            open_kwargs = {"mode": "a" if append else "w", "newline": ""}
        else:
            open_kwargs = {"mode": "ab" if append else "wb"}
        with open(path, **open_kwargs) as csv_file:
            writer = csv.writer(csv_file, delimiter=delimiter, **kwargs)
            if title:
                writer.writerow([title])
            for row in table:
                writer.writerow(row)
