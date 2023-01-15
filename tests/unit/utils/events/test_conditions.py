from unittest.mock import Mock

from pytest import mark

from gravitorch.utils.events import (
    EpochPeriodicCondition,
    IterationPeriodicCondition,
    PeriodicCondition,
)

#######################################
#     Tests for PeriodicCondition     #
#######################################


def test_periodic_condition_str():
    assert str(PeriodicCondition(3)).startswith("PeriodicCondition(freq=3,")


@mark.parametrize("freq", (1, 2, 3))
def test_periodic_condition_freq(freq: int):
    assert PeriodicCondition(freq).freq == freq


def test_periodic_condition_eq_true():
    assert PeriodicCondition(3) == PeriodicCondition(3)


def test_periodic_condition_eq_false_different_freq():
    assert PeriodicCondition(3) != PeriodicCondition(2)


def test_periodic_condition_eq_false_different_classes():
    assert PeriodicCondition(3) != EpochPeriodicCondition(engine=Mock(), freq=3)


def test_periodic_condition_freq_1():
    condition = PeriodicCondition(1)
    assert [condition() for _ in range(10)] == [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]


def test_periodic_condition_freq_2():
    condition = PeriodicCondition(2)
    assert [condition() for _ in range(10)] == [
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    ]


def test_periodic_condition_freq_3():
    condition = PeriodicCondition(3)
    assert [condition() for _ in range(10)] == [
        True,
        False,
        False,
        True,
        False,
        False,
        True,
        False,
        False,
        True,
    ]


############################################
#     Tests for EpochPeriodicCondition     #
############################################


def test_epoch_periodic_condition_str():
    engine = Mock()
    engine.epoch = -1
    assert str(EpochPeriodicCondition(engine, freq=2)).startswith("EpochPeriodicCondition(freq=2,")


@mark.parametrize("freq", (1, 2, 3))
def test_epoch_periodic_condition_freq(freq: int):
    assert EpochPeriodicCondition(engine=Mock(), freq=freq).freq == freq


def test_epoch_periodic_condition_eq_true():
    assert EpochPeriodicCondition(engine=Mock(), freq=3) == EpochPeriodicCondition(
        engine=Mock(), freq=3
    )


def test_epoch_periodic_condition_eq_false_different_freq():
    assert EpochPeriodicCondition(engine=Mock(), freq=3) != EpochPeriodicCondition(
        engine=Mock(), freq=2
    )


def test_epoch_periodic_condition_eq_false_different_classes():
    assert EpochPeriodicCondition(engine=Mock(), freq=3) != PeriodicCondition(3)


def test_epoch_periodic_condition_true():
    engine = Mock()
    condition = EpochPeriodicCondition(engine, 2)
    engine.epoch = 0
    assert condition()
    engine.epoch = 2
    assert condition()


def test_epoch_periodic_condition_false():
    engine = Mock()
    condition = EpochPeriodicCondition(engine, 2)
    engine.epoch = -1
    assert not condition()
    engine.epoch = 1
    assert not condition()


################################################
#     Tests for IterationPeriodicCondition     #
################################################


def test_iteration_periodic_condition_str():
    engine = Mock()
    engine.iteration = -1
    assert str(IterationPeriodicCondition(engine, freq=2)).startswith(
        "IterationPeriodicCondition(freq=2,"
    )


@mark.parametrize("freq", (1, 2, 3))
def test_iteration_periodic_condition_freq(freq: int):
    assert IterationPeriodicCondition(engine=Mock(), freq=freq).freq == freq


def test_iteration_periodic_condition_eq_true():
    assert IterationPeriodicCondition(engine=Mock(), freq=3) == IterationPeriodicCondition(
        engine=Mock(), freq=3
    )


def test_iteration_periodic_condition_eq_false_different_freq():
    assert IterationPeriodicCondition(engine=Mock(), freq=3) != IterationPeriodicCondition(
        engine=Mock(), freq=2
    )


def test_iteration_periodic_condition_eq_false_different_classes():
    assert IterationPeriodicCondition(engine=Mock(), freq=3) != PeriodicCondition(3)


def test_iteration_periodic_condition_true():
    engine = Mock()
    condition = IterationPeriodicCondition(engine, 2)
    engine.iteration = 0
    assert condition()
    engine.iteration = 2
    assert condition()


def test_iteration_periodic_condition_false():
    engine = Mock()
    condition = IterationPeriodicCondition(engine, 2)
    engine.iteration = -1
    assert not condition()
    engine.iteration = 1
    assert not condition()
