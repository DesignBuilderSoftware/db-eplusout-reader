from db_esofile_reader.exceptions import NoResults


class ResultsDictionary(dict):
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
    def sorted_items(self):
        if self:
            return [(k, self[k]) for k in sorted(self.keys())]
        else:
            raise NoResults("Cannot get sorted items, Results dictionary is empty. ")

    @property
    def scalar(self):
        try:
            return self.sorted_items[0][1][0]
        except IndexError:
            raise NoResults("Cannot get scalar value, first array is empty!")

    @property
    def first_array(self):
        return self.sorted_items[0][1]

    @property
    def first_variable(self):
        return self.sorted_items[0][0]

    @property
    def variables(self):
        return [v[0] for v in self.sorted_items]

    @property
    def arrays(self):
        return [v[1] for v in self.sorted_items]
