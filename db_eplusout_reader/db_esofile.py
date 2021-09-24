from db_eplusout_reader.constants import RP, TS, A, D, H, M
from db_eplusout_reader.exceptions import CollectionRequired
from db_eplusout_reader.processing.esofile_reader import process_eso_file
from db_eplusout_reader.processing.esofile_time import (
    convert_raw_date_data,
    get_n_days_from_cumulative,
)


class DBEsoFile:
    def __init__(self, environment_name, header, outputs, dates, n_days, days_of_week):
        """
        Represents processed EnergyPlus eso file output data.

        Results are stored in bins identified by output frequency.

        Parameters
        ----------
        environment_name : str
            A name of the environment.
        header : dict of {str, dict of {int, Variable}}
            Processed header dictionary.
        outputs : dict of {str, dict of {int, list of float}}
            Processed numeric outputs.
        dates : dict of {str, datetime}
            Parsed dates.
        n_days : dict of {str, list of int}
            Number of days for each step for monthly to runperiod frequencies.
        days_of_week:
            Day of week for each step for timestep to daily frequencies.

        Example
        -------
        environment_name 'TEST (01-01:31-12)'
        header {
            'hourly' : {
                Variable(key='B1:ZONE1', type='Zone Mean Air Temperature', units='C'): 322,
                Variable(key='B1:ZONE2', type='Zone Air Relative Humidity', units='%'): 304
                ...
            },
            'daily' : {
                Variable(key='B1:ZONE1', type='Zone Air Relative Humidity', units='%'): 521,
                Variable(key='B1:ZONE2', type='Zone Air Relative Humidity', units='%'): 565
                ...
            }
        }
        outputs {
            'hourly' : {
               322 : [17.906587634970627, 17.198486368112462, 16.653197201251096, ...]
               304 : [0.006551864336487204, 0.0061786832466626095, 0.005800374315868216, ...]
                ...
            },
            'daily' : {
                521 : [38.83017767728567, 48.74604212532369, 41.69013850729892, ...]
                565 : [43.25127519033924, 55.42681891740626, 42.215387940031526, ...]
                ...
            }
        }
        dates {
            'hourly' : [
                datetime.datetime(2002, 1, 1, 1, 0),
                datetime.datetime(2002, 1, 1, 2, 0),
                datetime.datetime(2002, 1, 1, 3, 0),
                ...
            ],
            'daily' : [
                datetime.datetime(2002, 1, 1, 0, 0),
                datetime.datetime(2002, 1, 2, 0, 0),
                datetime.datetime(2002, 1, 3, 0, 0),
                ...
        }
        n_days {
            'monthly': [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
            'annual': [365],
            'runperiod': [365]
        }
        days_of_week {
            'hourly': ['Tuesday', 'Tuesday', 'Tuesday', 'Tuesday', ...],
            'daily': ['Tuesday', 'Wednesday', 'Thursday', 'Friday', ...],
            ...
        }

        """
        self.environment_name = environment_name
        self.header = header
        self.outputs = outputs
        self.dates = dates
        self.n_days = n_days
        self.days_of_week = days_of_week

    @classmethod
    def _from_raw_outputs(cls, raw_outputs, year):
        dates = convert_raw_date_data(raw_outputs.dates, raw_outputs.days_of_week, year)
        n_days = get_n_days_from_cumulative(raw_outputs.cumulative_days)
        return cls(
            environment_name=raw_outputs.environment_name,
            header=raw_outputs.header,
            outputs=raw_outputs.outputs,
            dates=dates,
            n_days=n_days,
            days_of_week=raw_outputs.days_of_week,
        )

    @classmethod
    def from_path(cls, file_path, year=None):
        all_raw_outputs = process_eso_file(file_path)
        if len(all_raw_outputs) == 1:
            return cls._from_raw_outputs(all_raw_outputs[0], year)
        raise CollectionRequired(
            "Cannot process file {}. "
            "as there are multiple environments included.\n"
            "Use 'DBEsoFileCollection.from_path' "
            "to generate multiple files."
            "".format(file_path)
        )

    @property
    def frequencies(self):
        order = {TS: 0, H: 1, D: 2, M: 3, A: 4, RP: 5}
        return sorted(list(self.header.keys()), key=lambda x: order[x])


class DBEsoFileCollection:
    """
    Custom list to hold processed .eso file data.

    The collection can be populated by passing a path into
    'DBEsoFileCollection.from_path(some/path.eso)' class
    factory method.

    Parameters
    ----------
    db_eso_files : list of DBEsoFile or None
        A processed list of EnergyPlus output .eso files.

    """

    def __init__(self, db_eso_files=None):
        self._db_eso_files = [] if not db_eso_files else db_eso_files

    @classmethod
    def from_path(cls, file_path, year=None):
        all_raw_outputs = process_eso_file(file_path)
        db_eso_files = []
        for raw_outputs in all_raw_outputs:
            db_eso_file = DBEsoFile._from_raw_outputs(raw_outputs, year)
            db_eso_files.append(db_eso_file)
        return cls(db_eso_files)

    @property
    def environment_names(self):
        return [ef.environment_name for ef in self._db_eso_files]

    def __iter__(self):
        for item in self._db_eso_files:
            yield item

    def __getitem__(self, item):
        return self._db_eso_files[item]

    def __contains__(self, item):
        return item in self._db_eso_files

    def append(self, item):
        self._db_eso_files.append(item)

    def count(self):
        len(self._db_eso_files)

    def index(self, item):
        return self._db_eso_files.index(item)

    def extend(self, items):
        self._db_eso_files.extend(items)

    def insert(self, index, item):
        self._db_eso_files.insert(index, item)

    def pop(self, index):
        return self._db_eso_files.pop(index)

    def remove(self, item):
        self._db_eso_files.remove(item)

    def reverse(self):
        reversed(self._db_eso_files)

    def sort(self, reverse):
        self._db_eso_files.sort(key=lambda ef: ef.file_name, reverse=reverse)
