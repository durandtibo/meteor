from pathlib import Path
from unittest.mock import MagicMock, patch

import torch
from pytest import fixture, mark, raises

from gravitorch import constants as ct
from gravitorch.engines import BaseEngine, EngineEvents
from gravitorch.loops.observers import NoOpLoopObserver, PyTorchBatchSaver
from gravitorch.loops.training import AccelerateTrainingLoop
from gravitorch.testing import (
    DummyClassificationModel,
    DummyDataSource,
    DummyIterableDataset,
    accelerate_available,
    create_dummy_engine,
)
from gravitorch.utils.events import VanillaEventHandler
from gravitorch.utils.exp_trackers import EpochStep
from gravitorch.utils.history import EmptyHistoryError, MinScalarHistory
from gravitorch.utils.integrations import is_accelerate_available
from gravitorch.utils.profilers import NoOpProfiler, PyTorchProfiler

if is_accelerate_available():
    from accelerate import Accelerator
    from accelerate.state import AcceleratorState


@fixture(autouse=True)
def reset_accelerate_state() -> None:
    if is_accelerate_available():
        AcceleratorState._reset_state(reset_partial_state=True)


def increment_epoch_handler(engine: BaseEngine) -> None:
    engine.increment_epoch(2)


@accelerate_available
def test_accelerate_training_loop_str() -> None:
    assert str(AccelerateTrainingLoop()).startswith("AccelerateTrainingLoop(")


def test_accelerate_training_loop_missing_package() -> None:
    with patch("gravitorch.utils.integrations.is_accelerate_available", lambda *args: False):
        with raises(RuntimeError):
            AccelerateTrainingLoop()


@accelerate_available
def test_accelerate_training_loop_accelerator_none() -> None:
    assert isinstance(AccelerateTrainingLoop()._accelerator, Accelerator)


@accelerate_available
def test_accelerate_training_loop_accelerator_object() -> None:
    training_loop = AccelerateTrainingLoop(accelerator=Accelerator(cpu=True))
    assert isinstance(training_loop._accelerator, Accelerator)
    assert training_loop._accelerator.state.device.type == "cpu"


@accelerate_available
def test_accelerate_training_loop_accelerator_cpu_only() -> None:
    assert AccelerateTrainingLoop(accelerator={"cpu": True})._accelerator.state.device.type == "cpu"


@accelerate_available
@mark.parametrize("set_grad_to_none", (True, False))
def test_accelerate_training_loop_set_grad_to_none(set_grad_to_none: bool) -> None:
    assert (
        AccelerateTrainingLoop(set_grad_to_none=set_grad_to_none)._set_grad_to_none
        == set_grad_to_none
    )


@accelerate_available
def test_accelerate_training_loop_set_grad_to_none_default() -> None:
    assert not AccelerateTrainingLoop()._set_grad_to_none


@accelerate_available
@mark.parametrize("tag", ("pre-training", "custom name"))
def test_accelerate_training_loop_tag(tag: str) -> None:
    assert AccelerateTrainingLoop(tag=tag)._tag == tag


@accelerate_available
def test_accelerate_training_loop_tag_default() -> None:
    assert AccelerateTrainingLoop()._tag == "train"


@accelerate_available
def test_accelerate_training_loop_clip_grad_none() -> None:
    training_loop = AccelerateTrainingLoop()
    assert training_loop._clip_grad_fn is None
    assert training_loop._clip_grad_args == ()


@accelerate_available
def test_accelerate_training_loop_clip_grad_clip_grad_value_without_clip_value() -> None:
    training_loop = AccelerateTrainingLoop(clip_grad={"name": "clip_grad_value"})
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (0.25,)


@accelerate_available
@mark.parametrize("clip_value", (0.1, 1))
def test_accelerate_training_loop_clip_grad_clip_grad_value_with_clip_value(
    clip_value: float,
) -> None:
    training_loop = AccelerateTrainingLoop(
        clip_grad={"name": "clip_grad_value", "clip_value": clip_value}
    )
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (clip_value,)


@accelerate_available
def test_accelerate_training_loop_clip_grad_clip_grad_norm_without_max_norm_and_norm_type() -> None:
    training_loop = AccelerateTrainingLoop(clip_grad={"name": "clip_grad_norm"})
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (1, 2)


@accelerate_available
@mark.parametrize("max_norm", (0.1, 1))
@mark.parametrize("norm_type", (1, 2))
def test_accelerate_training_loop_clip_grad_clip_grad_norm_with_max_norm_and_norm_type(
    max_norm: float, norm_type: float
) -> None:
    training_loop = AccelerateTrainingLoop(
        clip_grad={"name": "clip_grad_norm", "max_norm": max_norm, "norm_type": norm_type}
    )
    assert callable(training_loop._clip_grad_fn)
    assert training_loop._clip_grad_args == (max_norm, norm_type)


@accelerate_available
def test_accelerate_training_loop_clip_grad_incorrect_name() -> None:
    with raises(ValueError):
        AccelerateTrainingLoop(clip_grad={"name": "incorrect name"})


@accelerate_available
def test_accelerate_training_loop_observer_default() -> None:
    assert isinstance(AccelerateTrainingLoop()._observer, NoOpLoopObserver)


@accelerate_available
def test_accelerate_training_loop_observer(tmp_path: Path) -> None:
    assert isinstance(
        AccelerateTrainingLoop(observer=PyTorchBatchSaver(tmp_path))._observer,
        PyTorchBatchSaver,
    )


@accelerate_available
def test_accelerate_training_loop_no_profiler() -> None:
    assert isinstance(AccelerateTrainingLoop()._profiler, NoOpProfiler)


@accelerate_available
def test_accelerate_training_loop_profiler_tensorboard() -> None:
    assert isinstance(
        AccelerateTrainingLoop(profiler=PyTorchProfiler(torch.profiler.profile()))._profiler,
        PyTorchProfiler,
    )


@accelerate_available
def test_accelerate_training_loop_train() -> None:
    engine = create_dummy_engine()
    AccelerateTrainingLoop().train(engine)
    assert engine.model.training
    assert engine.epoch == -1
    assert engine.iteration == 3
    loss_history = engine.get_history(f"train/{ct.LOSS}")
    assert isinstance(loss_history, MinScalarHistory)
    assert isinstance(loss_history.get_last_value(), float)
    assert len(loss_history.get_recent_history()) == 1


@accelerate_available
def test_accelerate_training_loop_train_loss_nan() -> None:
    engine = create_dummy_engine(model=DummyClassificationModel(loss_nan=True))
    AccelerateTrainingLoop().train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    with raises(EmptyHistoryError):
        engine.get_history(
            f"train/{ct.LOSS}"
        ).get_last_value()  # The loss is not logged because it is NaN


@accelerate_available
def test_accelerate_training_loop_train_with_loss_history() -> None:
    engine = create_dummy_engine()
    engine.add_history(MinScalarHistory(f"train/{ct.LOSS}"))
    engine.log_metric(f"train/{ct.LOSS}", 1, EpochStep(-1))
    AccelerateTrainingLoop().train(engine)
    loss_history = engine.get_history(f"train/{ct.LOSS}")
    assert isinstance(loss_history, MinScalarHistory)
    assert isinstance(loss_history.get_last_value(), float)
    assert len(loss_history.get_recent_history()) == 2


@accelerate_available
def test_accelerate_training_loop_train_set_grad_to_none_true() -> None:
    engine = create_dummy_engine()
    AccelerateTrainingLoop(set_grad_to_none=True).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    loss_history = engine.get_history(f"train/{ct.LOSS}")
    assert isinstance(loss_history, MinScalarHistory)
    assert isinstance(loss_history.get_last_value(), float)


@accelerate_available
def test_accelerate_training_loop_train_with_clip_grad_value() -> None:
    engine = create_dummy_engine()
    AccelerateTrainingLoop(clip_grad={"name": "clip_grad_value", "clip_value": 0.25}).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    assert isinstance(engine.get_history(f"train/{ct.LOSS}").get_last_value(), float)


@accelerate_available
def test_accelerate_training_loop_train_with_clip_grad_norm() -> None:
    engine = create_dummy_engine()
    AccelerateTrainingLoop(
        clip_grad={"name": "clip_grad_norm", "max_norm": 1, "norm_type": 2}
    ).train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 3
    assert isinstance(engine.get_history(f"train/{ct.LOSS}").get_last_value(), float)


# TODO: Comment this test because the current version of accelerate does not support
#  empty data loader
# @accelerate_available
# def test_accelerate_training_loop_train_empty_map_dataset() -> None:
#     engine = create_dummy_engine(data_source=FakeDataSource(train_dataset=EmptyFakeMapDataset()))
#     AccelerateTrainingLoop().train(engine)
#     assert engine.epoch == -1
#     assert engine.iteration == -1
#     with raises(EmptyHistoryError):
#         # The loss is not logged because there is no batch
#         engine.get_history(f"train/{ct.LOSS}").get_last_value()


@accelerate_available
def test_accelerate_training_loop_train_iterable_dataset() -> None:
    engine = create_dummy_engine(
        data_source=DummyDataSource(train_dataset=DummyIterableDataset(), batch_size=1)
    )
    AccelerateTrainingLoop().train(engine)
    assert engine.epoch == -1
    assert engine.iteration == 7
    assert isinstance(engine.get_history(f"train/{ct.LOSS}").get_last_value(), float)


# TODO: Comment this test because the current version of accelerate does not support
#  empty data loader
# @accelerate_available
# def test_accelerate_training_loop_train_empty_iterable_dataset() -> None:
#     engine = create_dummy_engine(
#         data_source=FakeDataSource(train_dataset=EmptyFakeIterableDataset(), batch_size=None)
#     )
#     AccelerateTrainingLoop().train(engine)
#     assert engine.epoch == -1
#     assert engine.iteration == -1
#     with raises(EmptyHistoryError):
#         # The loss is not logged because there is no batch
#         engine.get_history(f"train/{ct.LOSS}").get_last_value()


@accelerate_available
@mark.parametrize("event", (EngineEvents.TRAIN_EPOCH_STARTED, EngineEvents.TRAIN_EPOCH_COMPLETED))
def test_accelerate_training_loop_fire_event_train_epoch_events(event: str) -> None:
    engine = create_dummy_engine()
    engine.add_event_handler(
        event, VanillaEventHandler(increment_epoch_handler, handler_kwargs={"engine": engine})
    )
    engine.increment_epoch()  # simulate epoch 0
    AccelerateTrainingLoop().train(engine)
    assert engine.epoch == 2
    assert engine.iteration == 3


@accelerate_available
@mark.parametrize(
    "event",
    (
        EngineEvents.TRAIN_ITERATION_STARTED,
        EngineEvents.TRAIN_FORWARD_COMPLETED,
        EngineEvents.TRAIN_BACKWARD_COMPLETED,
        EngineEvents.TRAIN_ITERATION_COMPLETED,
    ),
)
def test_accelerate_training_loop_train_fire_event_train_iteration_events(event: str) -> None:
    engine = create_dummy_engine()
    engine.add_event_handler(
        event, VanillaEventHandler(increment_epoch_handler, handler_kwargs={"engine": engine})
    )
    engine.increment_epoch()  # simulate epoch 0
    AccelerateTrainingLoop().train(engine)
    assert engine.epoch == 8
    assert engine.iteration == 3


@accelerate_available
def test_accelerate_training_loop_train_with_observer() -> None:
    engine = create_dummy_engine()
    observer = MagicMock()
    AccelerateTrainingLoop(observer=observer).train(engine)
    observer.start.assert_called_once_with(engine)
    assert observer.update.call_count == 4
    observer.end.assert_called_once_with(engine)


@accelerate_available
def test_accelerate_training_loop_train_with_profiler() -> None:
    profiler = MagicMock()
    AccelerateTrainingLoop(profiler=profiler).train(engine=create_dummy_engine())
    assert profiler.__enter__().step.call_count == 4


@accelerate_available
def test_accelerate_training_loop_load_state_dict() -> None:
    AccelerateTrainingLoop().load_state_dict({})  # Verify it does not raise error


@accelerate_available
def test_accelerate_training_loop_state_dict() -> None:
    assert AccelerateTrainingLoop().state_dict() == {}
