class IncompleteFile(Exception):
    """ Exception raised when the file is not complete. """

    pass


class InvalidLineSyntax(Exception):
    """ Exception raised for an unexpected line syntax. """

    pass


class BlankLineError(Exception):
    """ Exception raised when eso file contains blank line.  """

    pass


class CollectionRequired(Exception):
    """ Exception raised when trying to process multienv file with DBEsoFile class."""

    pass


class LeapYearMismatch(Exception):
    """ Exception raised when requested year does not match real calendar. """

    pass


class StartDayMismatch(Exception):
    """ Exception raised when start day for given year does not match real calendar. """

    pass
