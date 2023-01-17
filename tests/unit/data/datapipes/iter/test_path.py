from pathlib import Path
from unittest.mock import Mock

from pytest import raises
from torch.utils.data import IterDataPipe

from gravitorch.data.datapipes.iter import (
    DirFilter,
    FileFilter,
    PathLister,
    SourceIterDataPipe,
)
from gravitorch.utils.io import save_text


def create_files(path: Path) -> None:
    save_text("", path.joinpath("file.txt"))
    save_text("", path.joinpath("dir/file.txt"))


###############################
#     Tests for DirFilter     #
###############################


def test_dir_filter_str():
    assert str(DirFilter(Mock(spec=IterDataPipe))).startswith("DirFilterIterDataPipe(")


def test_dir_filter_iter_recursive(tmp_path: Path):
    create_files(tmp_path)
    assert list(
        DirFilter(
            SourceIterDataPipe(
                [
                    tmp_path.joinpath("dir/file.txt"),
                    tmp_path.joinpath("dir/"),
                    tmp_path.joinpath("file.txt"),
                ]
            )
        )
    ) == [tmp_path.joinpath("dir/")]


def test_dir_filter_len(tmp_path: Path):
    with raises(TypeError):
        len(DirFilter(Mock(spec=IterDataPipe)))


################################
#     Tests for FileFilter     #
################################


def test_file_filter_str():
    assert str(FileFilter(Mock(spec=IterDataPipe))).startswith("FileFilterIterDataPipe(")


def test_file_filter_iter_recursive(tmp_path: Path):
    create_files(tmp_path)
    assert list(
        FileFilter(
            SourceIterDataPipe(
                [
                    tmp_path.joinpath("dir/file.txt"),
                    tmp_path.joinpath("dir/"),
                    tmp_path.joinpath("file.txt"),
                ]
            )
        )
    ) == [
        tmp_path.joinpath("dir/file.txt"),
        tmp_path.joinpath("file.txt"),
    ]


def test_file_filter_len(tmp_path: Path):
    with raises(TypeError):
        len(FileFilter(Mock(spec=IterDataPipe)))


################################
#     Tests for PathLister     #
################################


def test_path_lister_str():
    assert str(PathLister(Mock(spec=IterDataPipe))).startswith("PathListerIterDataPipe(")


def test_path_lister_iter_empty(tmp_path: Path):
    assert list(PathLister(SourceIterDataPipe([tmp_path]))) == []


def test_path_lister_iter(tmp_path: Path):
    create_files(tmp_path)
    assert list(PathLister(SourceIterDataPipe([tmp_path]), pattern="*.txt")) == [
        tmp_path.joinpath("file.txt")
    ]


def test_path_lister_iter_recursive(tmp_path: Path):
    create_files(tmp_path)
    assert list(PathLister(SourceIterDataPipe([tmp_path]), pattern="**/*.txt")) == [
        tmp_path.joinpath("dir/file.txt"),
        tmp_path.joinpath("file.txt"),
    ]


def test_path_lister_iter_deterministic_false(tmp_path: Path):
    create_files(tmp_path)
    assert set(
        PathLister(SourceIterDataPipe([tmp_path]), pattern="**/*.txt", deterministic=False)
    ) == {
        tmp_path.joinpath("dir/file.txt"),
        tmp_path.joinpath("file.txt"),
    }


def test_path_lister_len(tmp_path: Path):
    with raises(TypeError):
        len(PathLister(tmp_path))
