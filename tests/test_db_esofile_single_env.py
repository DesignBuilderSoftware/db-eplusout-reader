"""Tests for DBEsoFile behaviour with a single-environment ESO file.

Uses a small synthetic ESO file containing one environment reporting the
same variable at hourly, daily, monthly, annual and runperiod frequencies.
Covers the 'DBEsoFile.from_path' happy path, the 'frequencies' property,
the '.eso' branch of the top level 'get_results' function and datetime
validation without boundaries.
"""

from datetime import datetime

import pytest

from db_eplusout_reader import DBEsoFile, DBEsoFileCollection, Variable, get_results
from db_eplusout_reader.constants import RP, TS, A, D, H, M
from db_eplusout_reader.exceptions import CollectionRequired, NoResults

_HEADER = (
    "Program Version,EnergyPlus, Version 9.2.0-921312fa1d, YMD=2020.11.10 11:31\n"
    "1,5,Environment Title[],Latitude[deg],Longitude[deg],Time Zone[],Elevation[m]\n"
    "2,8,Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],Hour[],StartMinute[],EndMinute[],DayType\n"  # noqa: E501
    "3,5,Cumulative Day of Simulation[],Month[],Day of Month[],DST Indicator[1=yes 0=no],DayType  ! When Daily Report Variables Requested\n"  # noqa: E501
    "4,2,Cumulative Days of Simulation[],Month[]  ! When Monthly Report Variables Requested\n"
    "5,1,Cumulative Days of Simulation[] ! When Run Period Report Variables Requested\n"
    "6,1,Calendar Year of Simulation[] ! When Annual Report Variables Requested\n"
    "7,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Hourly\n"
    "8,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Daily\n"
    "9,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Monthly\n"
    "10,1,Environment,Site Outdoor Air Drybulb Temperature [C] !Annual\n"
    "11,1,Environment,Site Outdoor Air Drybulb Temperature [C] !RunPeriod\n"
    "End of Data Dictionary\n"
)

_SINGLE_ENV_BODY = (
    "1,TEST ENV, 0.0, 0.0, 0.0, 0.0\n"
    "2,1, 1, 1, 0, 1, 0.00,60.00,Tuesday\n"
    "7,20.0\n"
    "3,1, 1, 1, 0,Tuesday\n"
    "8,21.5\n"
    "4,31, 1\n"
    "9,22.0\n"
    "6,2013\n"
    "10,23.5\n"
    "5,31\n"
    "11,24.0\n"
    "End of Data\n"
)

_VARIABLE = Variable("Environment", "Site Outdoor Air Drybulb Temperature", "C")


@pytest.fixture(scope="module")
def single_env_eso_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("single_env") / "single_env.eso"
    path.write_text(_HEADER + _SINGLE_ENV_BODY)
    return str(path)


@pytest.fixture(scope="module")
def single_env_eso_file(single_env_eso_path):
    return DBEsoFile.from_path(single_env_eso_path)


class TestFromPath:
    def test_from_path_single_environment(self, single_env_eso_file):
        assert isinstance(single_env_eso_file, DBEsoFile)
        assert single_env_eso_file.environment_name == "TEST ENV"

    def test_from_path_multiple_environments_raises(self, tmp_path):
        eso = tmp_path / "multi_env.eso"
        eso.write_text(_HEADER + _SINGLE_ENV_BODY.replace("End of Data\n", "")
                       + _SINGLE_ENV_BODY.replace("TEST ENV", "SECOND ENV"))
        with pytest.raises(CollectionRequired, match="multiple environments"):
            DBEsoFile.from_path(str(eso))


class TestFrequencies:
    def test_frequencies_sorted(self, single_env_eso_file):
        assert single_env_eso_file.frequencies == [H, D, M, A, RP]


class TestSingleEnvResults:
    def test_hourly_results(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, H)
        assert rd.first_array == [20.0]
        # non-leap year starting on Tuesday 1 January resolves to 2019
        assert rd.time_series == [datetime(2019, 1, 1, 1)]

    def test_daily_results(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, D)
        assert rd.first_array == [21.5]

    def test_monthly_results(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, M)
        assert rd.first_array == [22.0]

    def test_annual_results(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, A)
        assert rd.first_array == [23.5]

    def test_runperiod_results(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, RP)
        assert rd.first_array == [24.0]

    def test_n_days_annual_derived_from_runperiod(self, single_env_eso_file):
        assert single_env_eso_file.n_days[M] == [31]
        assert single_env_eso_file.n_days[A] == [31]
        assert single_env_eso_file.n_days[RP] == [31]


class TestVariableMatching:
    def test_exact_match_is_case_insensitive(self, single_env_eso_file):
        variable = Variable("ENVIRONMENT", "site outdoor air drybulb temperature", "c")
        rd = single_env_eso_file.get_results(variable, H)
        assert rd.first_array == [20.0]

    def test_alike_partial_match(self, single_env_eso_file):
        variable = Variable("env", "drybulb", None)
        rd = single_env_eso_file.get_results(variable, H, alike=True)
        assert rd.first_variable == _VARIABLE
        assert rd.first_array == [20.0]

    def test_alike_false_rejects_partial_match(self, single_env_eso_file):
        variable = Variable("env", "drybulb", None)
        rd = single_env_eso_file.get_results(variable, H, alike=False)
        with pytest.raises(NoResults):
            _ = rd.first_array

    def test_none_fields_act_as_wildcards(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(Variable(None, None, None), H)
        assert rd.variables == [_VARIABLE]

    def test_list_of_variables(self, single_env_eso_file):
        rd = single_env_eso_file.get_results([_VARIABLE, Variable("No", "Match", "")], H)
        # only the matching variable is returned, without duplicates
        assert rd.variables == [_VARIABLE]

    def test_absent_frequency_returns_empty_results(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, TS)
        assert dict(rd) == {}
        assert rd.time_series == []


class TestDateFiltering:
    def test_inclusive_boundaries_keep_single_timestamp(self, single_env_eso_file):
        timestamp = datetime(2019, 1, 1, 1)
        rd = single_env_eso_file.get_results(
            _VARIABLE, H, start_date=timestamp, end_date=timestamp
        )
        assert rd.first_array == [20.0]
        assert rd.time_series == [timestamp]

    def test_start_date_after_data_filters_everything(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, H, start_date=datetime(2020, 1, 1))
        assert rd[_VARIABLE] == []
        assert rd.time_series == []

    def test_end_date_before_data_filters_everything(self, single_env_eso_file):
        rd = single_env_eso_file.get_results(_VARIABLE, H, end_date=datetime(2018, 12, 31))
        assert rd[_VARIABLE] == []
        assert rd.time_series == []


class TestCollectionFromMultiEnvPath:
    @pytest.fixture(scope="class")
    def multi_env_collection(self, tmp_path_factory):
        eso = tmp_path_factory.mktemp("multi_env") / "multi_env.eso"
        eso.write_text(
            _HEADER
            + _SINGLE_ENV_BODY.replace("End of Data\n", "")
            + _SINGLE_ENV_BODY.replace("TEST ENV", "SECOND ENV")
        )
        return DBEsoFileCollection.from_path(str(eso))

    def test_environment_names(self, multi_env_collection):
        assert multi_env_collection.environment_names == ["TEST ENV", "SECOND ENV"]

    def test_each_environment_holds_own_results(self, multi_env_collection):
        for eso_file in multi_env_collection:
            rd = eso_file.get_results(_VARIABLE, H)
            assert rd.first_array == [20.0]


class TestGetResultsEsoPathDispatch:
    def test_get_results_with_single_env_eso_path(self, single_env_eso_path):
        rd = get_results(single_env_eso_path, _VARIABLE, H)
        assert rd.first_variable == _VARIABLE
        assert rd.first_array == [20.0]


class TestValidateTime:
    def test_validate_time_no_boundaries(self, single_env_eso_file):
        assert single_env_eso_file._validate_time(datetime(2019, 1, 1), None, None) is True
