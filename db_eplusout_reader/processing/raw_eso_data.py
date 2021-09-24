from collections import defaultdict

from db_eplusout_reader.constants import RP, A, M


class RawOutputData:
    def __init__(self, environment_name, header):
        self.environment_name = environment_name
        self.header = header
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
        for frequency, variables in self.header.items():
            dates[frequency] = []
            if frequency in (M, A, RP):
                cumulative_days[frequency] = []
            else:
                days_of_week[frequency] = []
            for id_ in variables.values():
                outputs[frequency][id_] = []
        return outputs, dates, cumulative_days, days_of_week

    def initialize_next_outputs_step(self, frequency):
        for value in self.outputs[frequency].values():
            value.append(float("nan"))
