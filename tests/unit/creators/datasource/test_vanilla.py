from unittest.mock import Mock, patch

from objectory import OBJECT_TARGET
from pytest import mark

from gravitorch import constants as ct
from gravitorch.creators.datasource import VanillaDataSourceCreator
from gravitorch.datasources import BaseDataSource
from gravitorch.engines import BaseEngine
from gravitorch.testing import DummyDataSource

##############################################
#     Tests for VanillaDataSourceCreator     #
##############################################


def test_vanilla_data_source_creator_str() -> None:
    assert str(VanillaDataSourceCreator(config={})).startswith("VanillaDataSourceCreator(")


@mark.parametrize("attach_to_engine", (True, False))
def test_vanilla_data_source_creator_attach_to_engine(attach_to_engine: bool) -> None:
    assert (
        VanillaDataSourceCreator(
            config={},
            attach_to_engine=attach_to_engine,
        )._attach_to_engine
        == attach_to_engine
    )


@mark.parametrize("add_module_to_engine", (True, False))
def test_vanilla_data_source_creator_add_module_to_engine(add_module_to_engine: bool) -> None:
    assert (
        VanillaDataSourceCreator(
            config={}, add_module_to_engine=add_module_to_engine
        )._add_module_to_engine
        == add_module_to_engine
    )


def test_vanilla_data_source_creator_create() -> None:
    creator = VanillaDataSourceCreator(config={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"})
    data_source = creator.create(engine=Mock(spec=BaseEngine))
    assert isinstance(data_source, DummyDataSource)


def test_vanilla_data_source_creator_create_attach_to_engine_true() -> None:
    creator = VanillaDataSourceCreator(config={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"})
    engine = Mock(spec=BaseEngine)
    data_source = Mock(spec=BaseDataSource)
    setup_mock = Mock(return_value=data_source)
    with patch("gravitorch.creators.datasource.vanilla.setup_and_attach_data_source", setup_mock):
        assert creator.create(engine) == data_source
        setup_mock.assert_called_once_with(
            data_source={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"}, engine=engine
        )


def test_vanilla_data_source_creator_create_attach_to_engine_false() -> None:
    creator = VanillaDataSourceCreator(
        config={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"}, attach_to_engine=False
    )
    data_source = Mock(spec=BaseDataSource)
    setup_mock = Mock(return_value=data_source)
    with patch("gravitorch.creators.datasource.vanilla.setup_data_source", setup_mock):
        assert creator.create(engine=Mock(spec=BaseEngine)) == data_source
        setup_mock.assert_called_once_with(
            data_source={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"}
        )


def test_vanilla_data_source_creator_create_add_module_to_engine_true() -> None:
    engine = Mock(spec=BaseEngine)
    creator = VanillaDataSourceCreator(config={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"})
    data_source = creator.create(engine)
    assert isinstance(data_source, DummyDataSource)
    engine.add_module.assert_called_once_with(ct.DATA_SOURCE, data_source)


def test_vanilla_data_source_creator_create_add_module_to_engine_false() -> None:
    engine = Mock(spec=BaseEngine)
    creator = VanillaDataSourceCreator(
        config={OBJECT_TARGET: "gravitorch.testing.DummyDataSource"},
        add_module_to_engine=False,
    )
    data_source = creator.create(engine)
    assert isinstance(data_source, DummyDataSource)
    engine.add_module.assert_not_called()
