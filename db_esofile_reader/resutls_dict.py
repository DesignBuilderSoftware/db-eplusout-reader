from collections import OrderedDict

from db_esofile_reader.exceptions import NoResults


class ResultsDictionary(OrderedDict):
    """
    A dictionary like class with enhanced functionality to easily extract output arrays.

    Properties
    ----------
    sorted_items : list of tuple of (Variable, list of float)
        Lexicographically sorted dictionary (by key).
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

    @property
    def _items(self):
        if self:
            return self.items()
        else:
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
