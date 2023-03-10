import logging

import torch
from pytest import LogCaptureFixture, mark
from torch import nn
from torch.nn import LazyLinear, Linear, Parameter, UninitializedParameter

from gravitorch.nn import (
    ParameterSummary,
    get_parameter_summaries,
    show_parameter_summary,
)
from gravitorch.utils import get_available_devices

######################################
#     Tests for ParameterSummary     #
######################################


@mark.parametrize("device", get_available_devices())
def test_parameter_summary_from_parameter_device(device: str) -> None:
    device = torch.device(device)
    assert ParameterSummary.from_parameter(
        "weight", Parameter(torch.ones(6, 4, device=device))
    ) == ParameterSummary(
        name="weight",
        mean=1.0,
        median=1.0,
        std=0.0,
        min=1.0,
        max=1.0,
        learnable=True,
        shape=(6, 4),
        device=device,
    )


def test_parameter_summary_from_parameter_not_learnable() -> None:
    assert ParameterSummary.from_parameter(
        "weight", Parameter(torch.ones(6, 4), requires_grad=False)
    ) == ParameterSummary(
        name="weight",
        mean=1.0,
        median=1.0,
        std=0.0,
        min=1.0,
        max=1.0,
        learnable=False,
        shape=(6, 4),
        device=torch.device("cpu"),
    )


def test_parameter_summary_from_parameter_uninitialized() -> None:
    assert ParameterSummary.from_parameter("weight", UninitializedParameter()) == ParameterSummary(
        name="weight",
        mean="NI",
        median="NI",
        std="NI",
        min="NI",
        max="NI",
        learnable=True,
        shape="NI",
        device=torch.device("cpu"),
    )


def test_parameter_summary_from_parameter_no_parameters() -> None:
    assert ParameterSummary.from_parameter(
        "weight", Parameter(torch.ones(0, 4))
    ) == ParameterSummary(
        name="weight",
        mean="NP",
        median="NP",
        std="NP",
        min="NP",
        max="NP",
        learnable=True,
        shape=(0, 4),
        device=torch.device("cpu"),
    )


#############################################
#     Tests for get_parameter_summaries     #
#############################################


def test_get_parameter_summaries_linear() -> None:
    linear = Linear(4, 6)
    nn.init.ones_(linear.weight)
    nn.init.zeros_(linear.bias)
    assert get_parameter_summaries(linear) == [
        ParameterSummary(
            name="weight",
            mean=1.0,
            median=1.0,
            std=0.0,
            min=1.0,
            max=1.0,
            learnable=True,
            shape=(6, 4),
            device=torch.device("cpu"),
        ),
        ParameterSummary(
            name="bias",
            mean=0.0,
            median=0.0,
            std=0.0,
            min=0.0,
            max=0.0,
            learnable=True,
            shape=(6,),
            device=torch.device("cpu"),
        ),
    ]


def test_get_parameter_summaries_lazy_linear() -> None:
    assert get_parameter_summaries(LazyLinear(6)) == [
        ParameterSummary(
            name="weight",
            mean="NI",
            median="NI",
            std="NI",
            min="NI",
            max="NI",
            learnable=True,
            shape="NI",
            device=torch.device("cpu"),
        ),
        ParameterSummary(
            name="bias",
            mean="NI",
            median="NI",
            std="NI",
            min="NI",
            max="NI",
            learnable=True,
            shape="NI",
            device=torch.device("cpu"),
        ),
    ]


############################################
#     Tests for show_parameter_summary     #
############################################


@mark.parametrize("device", get_available_devices())
def test_show_parameter_summary_linear(device: str, caplog: LogCaptureFixture) -> None:
    device = torch.device(device)
    with caplog.at_level(logging.DEBUG):
        show_parameter_summary(nn.Linear(4, 6).to(device=device), tablefmt="fancy_outline")
        assert len(caplog.messages) > 0
