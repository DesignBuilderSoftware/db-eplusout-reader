from collections import defaultdict

from db_eplusout_reader.constants import RP, A, M


class RawOutputData:
    def __init__(self, environment_name, header, all_ids=None):
        self.environment_name = environment_name
        self.header = header
        # ``all_ids`` holds every line id per frequency, including ids that
        # collapse to the same Variable in ``header`` (e.g. a variable reported
        # both with and without a schedule). Output bins must cover all of them
        # so the body parser never encounters an unregistered id. Fall back to
        # the header ids when ``all_ids`` is not supplied.
        if all_ids is None:
            all_ids = {
                frequency: list(variables.values()) for frequency, variables in header.items()
            }
        self.all_ids = all_ids
        (
            self.outputs,
            self.dates,
            self.cumulative_days,
            self.days_of_week,
        ) = self.initialize_results_bins()

    def initialize_results_bins(self):
        outputs = defaultdict(dict)
        dates = {}
        cumulative_days = {}
        days_of_week = {}
        for frequency, ids in self.all_ids.items():
            dates[frequency] = []
            if frequency in (M, A, RP):
                cumulative_days[frequency] = []
            else:
                days_of_week[frequency] = []
            for id_ in ids:
                outputs[frequency][id_] = []
        return outputs, dates, cumulative_days, days_of_week

    def initialize_next_outputs_step(self, frequency):
        for value in self.outputs[frequency].values():
            value.append(float("nan"))
