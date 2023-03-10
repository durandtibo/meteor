from typing import Any

import torch
from pytest import mark

from gravitorch.utils.data_summary import NoOpDataSummary

#####################################
#     Tests for NoOpDataSummary     #
#####################################


def test_noop_data_summary_str() -> None:
    assert str(NoOpDataSummary()).startswith("NoOpDataSummary(")


@mark.parametrize("data", (1, "abc", torch.ones(2, 3)))
def test_noop_data_summary_add(data: Any) -> None:
    summary = NoOpDataSummary()
    summary.add(data)  # check it does not raise error


def test_noop_data_summary_reset() -> None:
    summary = NoOpDataSummary()
    summary.add(1)
    summary.reset()  # check it does not raise error


def test_noop_data_summary_summary() -> None:
    summary = NoOpDataSummary()
    assert summary.summary() == {}
