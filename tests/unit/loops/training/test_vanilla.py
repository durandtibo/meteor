import math
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import torch
from pytest import mark, raises
from torch import nn
from torch.optim import SGD, Optimizer

from gravitorch import constants as ct
from gravitorch.engines import BaseEngine, EngineEvents
from gravitorch.loops.training import VanillaTrainingLoop
from gravitorch.utils import get_available_devices
from gravitorch.utils.device_placement import (
    AutoDevicePlacement,
    CpuDevicePlacement,
    ManualDevicePlacement,
)
from gravitorch.utils.events import VanillaEventHandler
from gravitorch.utils.exp_trackers import EpochStep
from gravitorch.utils.history import EmptyHistoryError, MinScalarHistory
from gravitorch.utils.loop_observers import NoOpLoopObserver, PyTorchBatchSaver
from gravitorch.utils.profilers import NoOpProfiler, PyTorchProfiler
from tests.unit.engines.util import (
    EmptyFakeIterableDataset,
    EmptyFakeMapDataset,
    FakeDataSource,
    FakeIterableDataset,
    FakeModel,
    FakeModelWithNaN,
    create_engine,
)


def increment_epoch_handler(engine: BaseEngine) -> None:
    engine.increment_epoch(2)


#########################################
#     Tests for VanillaTrainingLoop     #
#########################################


def test_vanilla_training_loop_str():
    assert str(VanillaTrainingLoop()).startswith("VanillaTrainingLoop(")


@mark.parametrize("set_grad_to_none", (True, False))
def test_vanilla_training_loop_set_grad_to_none(set_grad_to_none: bool):
    assert (
        VanillaTrainingLoop(set_grad_to_none=set_grad_to_none)._set_grad_to_none == set_grad_to_none
    )


def test_vanilla_training_loop_set_grad_to_none_default():
    assert not VanillaTrainingLoop()._set_grad_to_none


def test_vanilla_training_loop_batch_device_placement_cpu():
    assert isinstance(
        VanillaTrainingLoop(batch_device_placement=CpuDevicePlacement())._batch_device_placement,
        CpuDevicePlacement,
    )


def test_vanilla_training_loop_batch_device_placement_default():
    assert isinstance(VanillaTrainingLoop()._batch_device_placement, AutoDevicePlacement)


@mark.parametrize("tag", ("pre-training", "custom name"))
def test_vanilla_training_loop_prefix(tag: str):
    assert VanillaTrainingLoop(tag=tag)._tag == tag


def test_vanilla_training_loop_prefix_default():
    assert VanillaTrainingLoop()._tag == "train"


def test_vanilla_training_loop_clip_grad_none():
    training_loop = VanillaTrainingLoop()
    assert training_loop._clip_grad_fn is None
    assert training_loop._clip_grad_args == ()


def test_vanilla_training_loop_clip_grad_clip_grad_value_without_clip_value():
    training_loop = VanillaTrainingLoop(clip_grad={"name": "clip_grad_value"})
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (0.25,)


@mark.parametrize("clip_value", (0.1, 1))
def test_vanilla_training_loop_clip_grad_clip_grad_value_with_clip_value(clip_value: float):
    training_loop = VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_value", "clip_value": clip_value}
    )
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (clip_value,)


def test_vanilla_training_loop_clip_grad_clip_grad_norm_without_max_norm_and_norm_type():
    training_loop = VanillaTrainingLoop(clip_grad={"name": "clip_grad_norm"})
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (1, 2)


@mark.parametrize("max_norm", (0.1, 1))
@mark.parametrize("norm_type", (1, 2))
def test_vanilla_training_loop_clip_grad_clip_grad_norm_with_max_norm_and_norm_type(
    max_norm: float, norm_type: float
):
    training_loop = VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_norm", "max_norm": max_norm, "norm_type": norm_type}
    )
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (max_norm, norm_type)


def test_vanilla_training_loop_clip_grad_incorrect_name():
    with raises(ValueError):
        VanillaTrainingLoop(clip_grad={"name": "incorrect name"})


def test_vanilla_training_loop_observer_default():
    assert isinstance(VanillaTrainingLoop()._observer, NoOpLoopObserver)


def test_vanilla_training_loop_observer(tmp_path: Path):
    assert isinstance(
        VanillaTrainingLoop(observer=PyTorchBatchSaver(tmp_path))._observer,
        PyTorchBatchSaver,
    )


def test_vanilla_training_loop_no_profiler():
    assert isinstance(VanillaTrainingLoop()._profiler, NoOpProfiler)


def test_vanilla_training_loop_profiler_tensorboard():
    assert isinstance(
        VanillaTrainingLoop(profiler=PyTorchProfiler(torch.profiler.profile()))._profiler,
        PyTorchProfiler,
    )


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.model.training
    assert engine.epoch == -1
    assert engine.iteration == 3
    loss_history = engine.get_history(f"train/{ct.LOSS}")
    assert isinstance(loss_history, MinScalarHistory)
    assert isinstance(loss_history.get_last_value(), float)
    assert len(loss_history.get_recent_history()) == 1


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_loss_nan(device: str):
    device = torch.device(device)
    engine = create_engine(model=FakeModelWithNaN())
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    with raises(EmptyHistoryError):
        engine.get_history(
            f"train/{ct.LOSS}"
        ).get_last_value()  # The loss is not logged because it is NaN


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_with_loss_history(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    engine.add_history(MinScalarHistory(f"train/{ct.LOSS}"))
    engine.log_metric(f"train/{ct.LOSS}", 1, EpochStep(-1))
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    loss_history = engine.get_history(f"train/{ct.LOSS}")
    assert isinstance(loss_history, MinScalarHistory)
    assert isinstance(loss_history.get_last_value(), float)
    assert len(loss_history.get_recent_history()) == 2


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_set_grad_to_none_true(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    VanillaTrainingLoop(
        set_grad_to_none=True, batch_device_placement=ManualDevicePlacement(device)
    ).train(engine)
    assert engine.model.training
    assert engine.epoch == -1
    assert engine.iteration == 3
    loss_history = engine.get_history(f"train/{ct.LOSS}")
    assert isinstance(loss_history, MinScalarHistory)
    assert isinstance(loss_history.get_last_value(), float)


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_with_clip_grad_value(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_value", "clip_value": 0.25},
        batch_device_placement=ManualDevicePlacement(device),
    ).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    assert isinstance(engine.get_history(f"train/{ct.LOSS}").get_last_value(), float)


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_with_clip_grad_norm(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_norm", "max_norm": 1, "norm_type": 2},
        batch_device_placement=ManualDevicePlacement(device),
    ).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    assert isinstance(engine.get_history(f"train/{ct.LOSS}").get_last_value(), float)


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_empty_map_dataset(device: str):
    device = torch.device(device)
    engine = create_engine(
        data_source=FakeDataSource(train_dataset=EmptyFakeMapDataset()),
        device=device,
    )
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == -1
    with raises(EmptyHistoryError):
        engine.get_history(
            f"train/{ct.LOSS}"
        ).get_last_value()  # The loss is not logged because there is no batch


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_iterable_dataset(device: str):
    device = torch.device(device)
    engine = create_engine(
        data_source=FakeDataSource(train_dataset=FakeIterableDataset(), batch_size=2),
        device=device,
    )
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    assert isinstance(engine.get_history(f"train/{ct.LOSS}").get_last_value(), float)


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_empty_iterable_dataset(device: str):
    device = torch.device(device)
    engine = create_engine(
        data_source=FakeDataSource(train_dataset=EmptyFakeIterableDataset(), batch_size=None),
        device=device,
    )
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == -1
    with raises(EmptyHistoryError):
        engine.get_history(
            f"train/{ct.LOSS}"
        ).get_last_value()  # The loss is not logged because there is no batch


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_batch_auto_device_placement(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    with patch("gravitorch.distributed.device", lambda *args, **kwargs: device):
        VanillaTrainingLoop().train(engine)
        assert engine.model.training
        assert engine.epoch == -1
        assert engine.iteration == 3
        loss_history = engine.get_history(f"train/{ct.LOSS}")
        assert isinstance(loss_history, MinScalarHistory)
        assert isinstance(loss_history.get_last_value(), float)
        assert len(loss_history.get_recent_history()) == 1


@mark.parametrize("device", get_available_devices())
@mark.parametrize("event", (EngineEvents.TRAIN_EPOCH_STARTED, EngineEvents.TRAIN_EPOCH_COMPLETED))
def test_vanilla_training_loop_fire_event_train_epoch_events(device: str, event: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    engine.add_event_handler(
        event, VanillaEventHandler(increment_epoch_handler, handler_kwargs={"engine": engine})
    )
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.epoch == 1
    assert engine.iteration == 3


@mark.parametrize("device", get_available_devices())
@mark.parametrize(
    "event",
    (
        EngineEvents.TRAIN_ITERATION_STARTED,
        EngineEvents.TRAIN_FORWARD_COMPLETED,
        EngineEvents.TRAIN_BACKWARD_COMPLETED,
        EngineEvents.TRAIN_ITERATION_COMPLETED,
    ),
)
def test_vanilla_training_loop_fire_event_train_iteration_events(device: str, event: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    engine.add_event_handler(
        event, VanillaEventHandler(increment_epoch_handler, handler_kwargs={"engine": engine})
    )
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device)).train(engine)
    assert engine.epoch == 7
    assert engine.iteration == 3


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_with_observer(device: str):
    device = torch.device(device)
    engine = create_engine(device=device)
    observer = MagicMock()
    VanillaTrainingLoop(
        observer=observer, batch_device_placement=ManualDevicePlacement(device)
    ).train(engine)
    observer.start.assert_called_once_with(engine)
    assert observer.update.call_count == 4
    observer.end.assert_called_once_with(engine)


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_with_profiler(device: str):
    device = torch.device(device)
    profiler = MagicMock()
    VanillaTrainingLoop(
        profiler=profiler, batch_device_placement=ManualDevicePlacement(device)
    ).train(engine=create_engine(device=device))
    assert profiler.__enter__().step.call_count == 4


def test_vanilla_training_loop_load_state_dict():
    VanillaTrainingLoop().load_state_dict({})  # Verify it does not raise error


def test_vanilla_training_loop_state_dict():
    assert VanillaTrainingLoop().state_dict() == {}


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_one_batch_fired_events(device: str):
    device = torch.device(device)
    engine = Mock(spec=BaseEngine)
    model = FakeModel().to(device=device)
    VanillaTrainingLoop(batch_device_placement=ManualDevicePlacement(device))._train_one_batch(
        engine=engine,
        model=model,
        optimizer=SGD(model.parameters(), lr=0.01),
        batch={ct.INPUT: torch.ones(8, 4), ct.TARGET: torch.ones(8, dtype=torch.long)},
    )
    assert engine.fire_event.call_args_list == [
        ((EngineEvents.TRAIN_ITERATION_STARTED,), {}),
        ((EngineEvents.TRAIN_FORWARD_COMPLETED,), {}),
        ((EngineEvents.TRAIN_BACKWARD_COMPLETED,), {}),
        ((EngineEvents.TRAIN_ITERATION_COMPLETED,), {}),
    ]


@mark.parametrize("device", get_available_devices())
@mark.parametrize("set_grad_to_none", (True, False))
def test_vanilla_training_loop_train_one_batch_set_grad_to_none(
    device: str, set_grad_to_none: bool
):
    device = torch.device(device)
    engine = Mock(spec=BaseEngine)
    model = FakeModel().to(device=device)
    out = VanillaTrainingLoop(
        set_grad_to_none=set_grad_to_none,
        batch_device_placement=ManualDevicePlacement(device),
    )._train_one_batch(
        engine=engine,
        model=model,
        optimizer=SGD(model.parameters(), lr=0.01),
        batch={ct.INPUT: torch.ones(8, 4), ct.TARGET: torch.ones(8, dtype=torch.long)},
    )
    assert isinstance(out, dict)
    assert torch.is_tensor(out[ct.LOSS])
    assert out[ct.LOSS].device == device


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_one_batch_clip_grad_value(device: str):
    device = torch.device(device)
    engine = Mock(spec=BaseEngine)
    model = FakeModel().to(device=device)
    out = VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_value", "clip_value": 0.25},
        batch_device_placement=ManualDevicePlacement(device),
    )._train_one_batch(
        engine=engine,
        model=model,
        optimizer=SGD(model.parameters(), lr=0.01),
        batch={ct.INPUT: torch.ones(8, 4), ct.TARGET: torch.ones(8, dtype=torch.long)},
    )
    assert isinstance(out, dict)
    assert torch.is_tensor(out[ct.LOSS])
    assert out[ct.LOSS].device == device


@mark.parametrize("device", get_available_devices())
def test_vanilla_training_loop_train_one_batch_clip_grad_norm(device: str):
    device = torch.device(device)
    engine = Mock(spec=BaseEngine)
    model = FakeModel().to(device=device)
    out = VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_norm", "max_norm": 1, "norm_type": 2},
        batch_device_placement=ManualDevicePlacement(device),
    )._train_one_batch(
        engine=engine,
        model=model,
        optimizer=SGD(model.parameters(), lr=0.01),
        batch={ct.INPUT: torch.ones(8, 4), ct.TARGET: torch.ones(8, dtype=torch.long)},
    )
    assert isinstance(out, dict)
    assert torch.is_tensor(out[ct.LOSS])
    assert out[ct.LOSS].device == device


def test_vanilla_training_loop_train_one_batch_loss_nan():
    engine = Mock(spec=BaseEngine)
    model = Mock(spec=nn.Module, return_value={ct.LOSS: torch.tensor(math.nan)})
    optimizer = Mock(spec=Optimizer)
    out = VanillaTrainingLoop(
        clip_grad={"name": "clip_grad_norm", "max_norm": 1, "norm_type": 2}
    )._train_one_batch(
        engine=engine,
        model=model,
        optimizer=optimizer,
        batch={ct.INPUT: torch.ones(8, 4), ct.TARGET: torch.ones(8, dtype=torch.long)},
    )
    assert isinstance(out, dict)
    assert torch.isnan(out[ct.LOSS])
    assert engine.fire_event.call_args_list == [
        ((EngineEvents.TRAIN_ITERATION_STARTED,), {}),
        ((EngineEvents.TRAIN_FORWARD_COMPLETED,), {}),
        ((EngineEvents.TRAIN_ITERATION_COMPLETED,), {}),
    ]