class IncompleteFile(Exception):
    """Exception raised when the file is not complete."""


class InvalidLineSyntax(Exception):
    """Exception raised for an unexpected line syntax."""


class BlankLineError(Exception):
    """Exception raised when eso file contains blank line."""


class CollectionRequired(Exception):
    """Exception raised when trying to process multienv file with DBEsoFile class."""


class LeapYearMismatch(Exception):
    """Exception raised when requested year does not match real calendar."""


class StartDayMismatch(Exception):
    """Exception raised when start day for given year does not match real calendar."""


class NoResults(Exception):
    """Exception raised when numeric outputs are requsted in empty results dictionary."""


class InvalidShape(Exception):
    """Exception raised when table does not have uniform number of items in each column."""
