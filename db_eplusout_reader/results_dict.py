from collections import OrderedDict

from db_eplusout_reader.exceptions import NoResults


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
        super(ResultsDictionary, self).__init__()
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
        except IndexError as error:
            raise NoResults("Cannot get scalar value, first array is empty!") from error

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

    def to_csv(self, path):
        pass


class ResultsHandler:
    @classmethod
    def to_table(cls, results_dictionary):
        sub_tables = {}
        for frequency in results_dictionary.frequencies:
            sub_tables[frequency] = results_dictionary.get_results_for_frequency(
                frequency
            )
